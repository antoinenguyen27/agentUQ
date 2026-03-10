import asyncio
from dataclasses import dataclass, field

from agentuq.adapters.fireworks import FireworksAdapter
from agentuq.adapters.gemini import GeminiAdapter
from agentuq.adapters.litellm import LiteLLMAdapter, probe_litellm_capability
from agentuq.adapters.openai_agents import OpenAIAgentsAdapter, latest_raw_response, model_settings_with_logprobs
from agentuq.adapters.openrouter import OpenRouterAdapter, probe_openrouter_model
from agentuq.adapters.together import TogetherAdapter
from agentuq.analysis.analyzer import Analyzer
from agentuq.integrations.langchain_middleware import UQMiddleware, analyze_after_model_call, guard_before_tool_execution
from agentuq.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from agentuq.request_params import request_params
from agentuq.schemas.config import UQConfig
from agentuq.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken
from agentuq.schemas.results import Action


def _chat_response() -> dict:
    return {
        "id": "chat_1",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "content": "Checking.",
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "weather_lookup", "arguments": '{"city":"Paris"}'}}
                    ],
                },
                "logprobs": {
                    "content": [
                        {"token": "Checking", "logprob": -0.2, "top_logprobs": [{"token": "Checking", "logprob": -0.2}, {"token": "Looking", "logprob": -0.9}]},
                        {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -1.5}]},
                    ]
                },
            }
        ],
    }


def _responses_payload() -> dict:
    return {
        "id": "resp_1",
        "model": "gpt-4.1-mini",
        "output": [
            {"type": "function_call", "name": "weather_lookup", "arguments": '{"city":"Paris"}'},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Checking.",
                        "logprobs": [
                            {"token": "Checking", "logprob": -0.2, "top_logprobs": [{"token": "Checking", "logprob": -0.2}, {"token": "Looking", "logprob": -0.9}]},
                            {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -1.5}]},
                        ],
                    }
                ],
            },
        ],
    }


def test_request_params_cover_supported_providers():
    openai = request_params("openai", mode="canonical", topk=7)
    assert openai["include"] == ["message.output_text.logprobs"]
    assert openai["top_logprobs"] == 7
    assert openai["temperature"] == 0.0
    assert "logprobs" not in openai

    openai_chat = request_params("openai", mode="canonical", topk=7, transport="chat")
    assert openai_chat["logprobs"] is True
    assert openai_chat["top_logprobs"] == 7
    assert "include" not in openai_chat

    openrouter = request_params("openrouter", mode="realized", topk=3)
    assert openrouter["provider"]["require_parameters"] is True
    assert openrouter["top_logprobs"] == 3

    litellm = request_params("litellm", mode="canonical", topk=2)
    assert litellm["drop_params"] is False
    assert litellm["temperature"] == 0.0

    gemini = request_params("gemini", topk=4)
    assert gemini["responseLogprobs"] is True
    assert gemini["logprobs"] == 4

    fireworks = request_params("fireworks", topk=5)
    assert fireworks["logprobs"] is True
    assert fireworks["top_logprobs"] == 5

    together = request_params("together", topk=6)
    assert together["logprobs"] == 6
    assert "top_logprobs" not in together

    assert GeminiAdapter().capability_report({"candidates": []}, gemini).request_attempted_topk == 4
    assert FireworksAdapter().capability_report({"choices": []}, fireworks).request_attempted_topk == 5
    assert OpenRouterAdapter().capability_report({"choices": []}, openrouter).request_attempted_topk == 3
    assert LiteLLMAdapter().capability_report({"choices": []}, litellm).request_attempted_topk == 2
    assert TogetherAdapter().capability_report({"choices": []}, together).request_attempted_topk == 6
    assert OpenAIAgentsAdapter().capability_report({"output": []}, {"response_include": ["message.output_text.logprobs"], "top_logprobs": 7}).request_attempted_logprobs is True


def test_request_params_unknown_provider_raises():
    try:
        request_params("unknown-provider")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    try:
        request_params("openai", transport="invalid")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_probe_helpers_and_declared_support():
    litellm_probe = probe_litellm_capability("openai/gpt-4o-mini", supported_openai_params=["logprobs", "top_logprobs"])
    assert litellm_probe["supports_logprobs"] is True
    assert litellm_probe["supports_top_logprobs"] is True

    openrouter_probe = probe_openrouter_model("openai/gpt-4o-mini", supported_parameters=["logprobs"])
    assert openrouter_probe["supports_logprobs"] is True
    assert openrouter_probe["supports_top_logprobs"] is False

    litellm_cap = LiteLLMAdapter().capability_report(_chat_response(), {"logprobs": True, "top_logprobs": 2, "supported_openai_params": ["logprobs", "top_logprobs"]})
    openrouter_cap = OpenRouterAdapter().capability_report(_chat_response(), {"logprobs": True, "top_logprobs": 2, "supported_parameters": ["logprobs", "top_logprobs"]})
    assert litellm_cap.provider_declared_support is True
    assert openrouter_cap.provider_declared_support is True


def test_openai_agents_helpers():
    settings = model_settings_with_logprobs(top_logprobs=4)
    assert settings["top_logprobs"] == 4
    assert settings["response_include"] == ["message.output_text.logprobs"]

    agent_record = OpenAIAgentsAdapter().capture(_responses_payload(), {"response_include": ["message.output_text.logprobs"], "top_logprobs": 2})
    assert agent_record.provider == "openai"
    assert agent_record.structured_blocks[0].type == "function_call"

    run_result = type("RunResult", (), {"raw_responses": [{"id": "resp_latest"}]})()
    assert latest_raw_response(run_result)["id"] == "resp_latest"

    try:
        latest_raw_response(object())
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError when raw_responses are unavailable")


def test_fireworks_adapter_prefers_openai_compatible_logprobs_content():
    fireworks_record = FireworksAdapter().capture(
        {
            "id": "fw_1",
            "model": "accounts/fireworks/models/test",
            "choices": [
                {
                    "message": {"content": "SELECT email"},
                    "logprobs": {
                        "content": [
                            {"token": "SELECT", "logprob": -0.2, "top_logprobs": [{"token": "SELECT", "logprob": -0.2}, {"token": "UPDATE", "logprob": -1.0}]},
                            {"token": " email", "logprob": -0.1, "top_logprobs": [{"token": " email", "logprob": -0.1}, {"token": " id", "logprob": -0.4}]},
                        ]
                    },
                }
            ],
        },
        {"logprobs": True, "top_logprobs": 2},
    )
    assert fireworks_record.provider == "fireworks"
    assert fireworks_record.selected_tokens == ["SELECT", " email"]
    assert fireworks_record.metadata["fireworks_logprobs_source"] == "openai_compatible_content"


def test_fireworks_adapter_supports_legacy_logprob_arrays():
    fireworks_record = FireworksAdapter().capture(
        {
            "id": "fw_1",
            "model": "accounts/fireworks/models/test",
            "choices": [
                {
                    "message": {"content": "SELECT email"},
                    "logprobs": {
                        "tokens": ["SELECT", " email"],
                        "token_logprobs": [-0.2, -0.1],
                        "top_logprobs": [
                            [{"token": "SELECT", "logprob": -0.2}, {"token": "UPDATE", "logprob": -1.0}],
                            [{"token": " email", "logprob": -0.1}, {"token": " id", "logprob": -0.4}],
                        ],
                    },
                }
            ],
        },
        {"logprobs": True, "top_logprobs": 2},
    )
    assert fireworks_record.provider == "fireworks"
    assert fireworks_record.selected_tokens == ["SELECT", " email"]
    assert fireworks_record.metadata["fireworks_logprobs_source"] == "legacy_token_arrays"


@dataclass
class DummyResponse:
    content: str = "Checking."
    response_metadata: dict = field(
        default_factory=lambda: {
            "model_name": "gpt-4o-mini",
            "logprobs": _chat_response()["choices"][0]["logprobs"],
        }
    )
    additional_kwargs: dict = field(default_factory=dict)
    tool_calls: list = field(
        default_factory=lambda: [{"id": "call_1", "name": "weather_lookup", "args": {"city": "Paris"}, "type": "tool_call"}]
    )


@dataclass
class RiskyToolResponse:
    content: str = "Checking."
    response_metadata: dict = field(
        default_factory=lambda: {
            "model_name": "gpt-4o-mini",
            "logprobs": {
                "content": [
                    {"token": "Checking", "logprob": -2.2, "top_logprobs": [{"token": "Checking", "logprob": -2.2}, {"token": "Looking", "logprob": -2.3}]},
                    {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -1.0}]},
                ]
            },
        }
    )
    additional_kwargs: dict = field(default_factory=dict)
    tool_calls: list = field(
        default_factory=lambda: [{"id": "call_1", "name": "weather_lookup", "args": {"city": "Paris"}, "type": "tool_call"}]
    )


@dataclass
class DummyModel:
    invoked_with: tuple = ()

    def invoke(self, *args, **kwargs):
        self.invoked_with = (args, kwargs)
        return DummyResponse()

    async def ainvoke(self, *args, **kwargs):
        self.invoked_with = (args, kwargs)
        return DummyResponse()


@dataclass
class BoundDummyModel:
    invoked_with: tuple = ()
    kwargs: dict = field(default_factory=lambda: {"logprobs": True, "top_logprobs": 2})
    bound: object = field(
        default_factory=lambda: type(
            "BoundOpenAIModel",
            (),
            {"model_name": "gpt-4o-mini", "temperature": 0.0, "top_p": 1.0},
        )()
    )

    def invoke(self, *args, **kwargs):
        self.invoked_with = (args, kwargs)
        return DummyResponse()

    async def ainvoke(self, *args, **kwargs):
        self.invoked_with = (args, kwargs)
        return DummyResponse()


def _grounded_tool_result() -> tuple:
    raw_text = 'weather_lookup{"city":"Paris"}'
    record = GenerationRecord(
        provider="synthetic",
        transport="unit_test",
        model="gpt-test",
        temperature=0.6,
        top_p=1.0,
        raw_text=raw_text,
        selected_tokens=["weather_lookup", '{"city"', ":", '"Paris"', "}"],
        selected_logprobs=[-2.2, -0.2, -0.1, -0.3, -0.1],
        top_logprobs=[
            [TopToken(token="weather_lookup", logprob=-2.2), TopToken(token="search_web", logprob=-2.3)],
            [TopToken(token='{"city"', logprob=-0.2), TopToken(token='{"location"', logprob=-1.0)],
            [TopToken(token=":", logprob=-0.1), TopToken(token=",", logprob=-1.2)],
            [TopToken(token='"Paris"', logprob=-0.3), TopToken(token='"London"', logprob=-0.7)],
            [TopToken(token="}", logprob=-0.1), TopToken(token="]", logprob=-1.0)],
        ],
        structured_blocks=[
            StructuredBlock(
                type="function_call",
                name="weather_lookup",
                arguments='{"city":"Paris"}',
                text=raw_text,
                char_start=0,
                char_end=len(raw_text),
                metadata={"token_grounded": True},
            )
        ],
        metadata={"request_logprobs": True, "request_topk": 2},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=2,
        structured_blocks=True,
        function_call_structure=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
    )
    result = Analyzer(UQConfig(mode="realized")).analyze_step(record, capability)
    tool_name_segment = next(segment for segment in result.segments if segment.kind == "tool_name")
    return result, tool_name_segment


def test_langchain_analysis_attaches_uq_result_without_tool_grounding():
    response = DummyResponse()
    request_meta = {"logprobs": True, "top_logprobs": 2, "deterministic": True}
    result = analyze_after_model_call(response, UQConfig(), request_meta)
    assert "uq_result" in response.response_metadata
    assert result.decision is not None
    assert all(segment.kind != "tool_name" for segment in result.segments)
    assert guard_before_tool_execution("weather_lookup", result) == Action.CONTINUE


def test_guard_before_tool_execution_uses_explicit_grounded_tool_segments():
    result, tool_name_segment = _grounded_tool_result()
    assert guard_before_tool_execution("weather_lookup", result) == result.decision.segment_actions[tool_name_segment.id]


def test_uqmiddleware_sync_and_async():
    model = DummyModel()
    middleware = UQMiddleware(model, UQConfig())
    response = middleware.invoke("prompt", config={"metadata": {"logprobs": True, "top_logprobs": 2, "deterministic": True}})
    assert "uq_result" in response.response_metadata

    async_response = asyncio.run(
        middleware.ainvoke("prompt", config={"metadata": {"logprobs": True, "top_logprobs": 2, "deterministic": True}})
    )
    assert "uq_result" in async_response.response_metadata


def test_uqmiddleware_infers_request_meta_from_bound_model():
    model = BoundDummyModel()
    middleware = UQMiddleware(model, UQConfig())
    response = middleware.invoke("prompt")
    assert response.response_metadata["uq_result"]["mode"] == "canonical"


def test_analyze_after_model_call_infers_logprob_request_from_response_metadata():
    response = DummyResponse()
    result = analyze_after_model_call(response, UQConfig())
    assert result.capability_level.value == "full"
    assert result.mode == "realized"


def test_langgraph_state_helpers_do_not_interrupt_for_ungrounded_tool_calls():
    response = RiskyToolResponse()
    state = enrich_graph_state({}, response, UQConfig(), {"logprobs": True, "top_logprobs": 2, "deterministic": True})
    assert "uq_result" in state
    assert should_interrupt_before_tool("weather_lookup", state) is False
    assert should_interrupt_before_tool("other_tool", state) is False


def test_langgraph_state_helpers_interrupt_for_grounded_tool_segments():
    result, _tool_name_segment = _grounded_tool_result()
    state = {"uq_result": result.model_dump(mode="json")}
    assert should_interrupt_before_tool("weather_lookup", state) is True
    assert should_interrupt_before_tool("other_tool", state) is False
