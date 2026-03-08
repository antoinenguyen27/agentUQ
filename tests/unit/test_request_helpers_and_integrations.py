import asyncio
from dataclasses import dataclass, field

from uq_runtime.adapters.fireworks import FireworksAdapter
from uq_runtime.adapters.litellm import LiteLLMAdapter, probe_litellm_capability
from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter, model_settings_with_logprobs
from uq_runtime.adapters.openrouter import OpenRouterAdapter, probe_openrouter_model
from uq_runtime.integrations.langchain_middleware import UQMiddleware, analyze_after_model_call, guard_before_tool_execution
from uq_runtime.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from uq_runtime.integrations.openai_wrappers import UQWrappedOpenAI
from uq_runtime.request_params import request_params
from uq_runtime.schemas.config import UQConfig


def _chat_response() -> dict:
    return {
        "id": "chat_1",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "weather_lookup", "arguments": '{"city":"Paris"}'}}
                    ],
                },
                "logprobs": {
                    "content": [
                        {"token": "weather_lookup", "logprob": -0.2, "top_logprobs": [{"token": "weather_lookup", "logprob": -0.2}, {"token": "search", "logprob": -0.9}]},
                        {"token": '{"city"', "logprob": -0.2, "top_logprobs": [{"token": '{"city"', "logprob": -0.2}, {"token": '{"location"', "logprob": -1.0}]},
                        {"token": ":", "logprob": -0.1, "top_logprobs": [{"token": ":", "logprob": -0.1}, {"token": ",", "logprob": -1.5}]},
                        {"token": '"Paris"', "logprob": -0.3, "top_logprobs": [{"token": '"Paris"', "logprob": -0.3}, {"token": '"London"', "logprob": -0.6}]},
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
                        "text": "",
                        "logprobs": [
                            {"token": "weather_lookup", "logprob": -0.2, "top_logprobs": [{"token": "weather_lookup", "logprob": -0.2}, {"token": "search", "logprob": -0.9}]},
                            {"token": '{"city"', "logprob": -0.2, "top_logprobs": [{"token": '{"city"', "logprob": -0.2}, {"token": '{"location"', "logprob": -1.0}]},
                            {"token": ":", "logprob": -0.1, "top_logprobs": [{"token": ":", "logprob": -0.1}, {"token": ",", "logprob": -1.5}]},
                            {"token": '"Paris"', "logprob": -0.3, "top_logprobs": [{"token": '"Paris"', "logprob": -0.3}, {"token": '"London"', "logprob": -0.6}]},
                        ],
                    }
                ],
            },
        ],
    }


def test_request_params_cover_supported_providers():
    openai = request_params("openai", mode="canonical", topk=7)
    assert openai["include_output_text_logprobs"] is True
    assert openai["top_logprobs"] == 7
    assert openai["temperature"] == 0.0

    openrouter = request_params("openrouter", mode="realized", topk=3)
    assert openrouter["provider"]["require_parameters"] is True
    assert openrouter["top_logprobs"] == 3

    litellm = request_params("litellm", mode="canonical", topk=2)
    assert litellm["drop_params"] is False
    assert litellm["deterministic"] is True

    gemini = request_params("gemini", topk=4)
    assert gemini["responseLogprobs"] is True
    assert gemini["logprobs"] == 4

    fireworks = request_params("fireworks", topk=5)
    assert fireworks["logprobs"] is True
    assert fireworks["top_logprobs"] == 5

    together = request_params("together", topk=6)
    assert together["logprobs"] == 6
    assert together["top_logprobs"] is None


def test_request_params_unknown_provider_raises():
    try:
        request_params("unknown-provider")
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


def test_openai_agents_helpers_and_fireworks_adapter():
    settings = model_settings_with_logprobs(top_logprobs=4)
    assert settings["top_logprobs"] == 4
    assert settings["include"] == ["message.output_text.logprobs"]

    agent_record = OpenAIAgentsAdapter().capture(_responses_payload(), {"include_output_text_logprobs": True, "top_logprobs": 2})
    assert agent_record.provider == "openai"
    assert agent_record.structured_blocks[0].type == "function_call"

    fireworks_record = FireworksAdapter().capture(_chat_response(), {"logprobs": True, "top_logprobs": 2})
    assert fireworks_record.provider == "fireworks"


@dataclass
class DummyResponse:
    content: str = ""
    response_metadata: dict = field(
        default_factory=lambda: {
            "model_name": "gpt-4o-mini",
            "logprobs": _chat_response()["choices"][0]["logprobs"],
        }
    )
    additional_kwargs: dict = field(
        default_factory=lambda: {"tool_calls": _chat_response()["choices"][0]["message"]["tool_calls"]}
    )


@dataclass
class RiskyToolResponse:
    content: str = ""
    response_metadata: dict = field(
        default_factory=lambda: {
            "model_name": "gpt-4o-mini",
            "logprobs": {
                "content": [
                    {"token": "weather_lookup", "logprob": -2.2, "top_logprobs": [{"token": "weather_lookup", "logprob": -2.2}, {"token": "search_web", "logprob": -2.3}]},
                    {"token": '{"city"', "logprob": -0.2, "top_logprobs": [{"token": '{"city"', "logprob": -0.2}, {"token": '{"location"', "logprob": -0.9}]},
                ]
            },
        }
    )
    additional_kwargs: dict = field(
        default_factory=lambda: {"tool_calls": [{"id": "call_1", "function": {"name": "weather_lookup", "arguments": '{"city":"Paris"}'}}]}
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


def test_langchain_analysis_and_guard_helpers():
    response = DummyResponse()
    request_meta = {"logprobs": True, "top_logprobs": 2, "deterministic": True}
    result = analyze_after_model_call(response, UQConfig(), request_meta)
    assert "uq_result" in response.response_metadata
    assert result.decision is not None
    assert guard_before_tool_execution("weather_lookup", result) == result.decision.segment_actions[next(seg.id for seg in result.segments if seg.kind == "tool_name")]


def test_uqmiddleware_sync_and_async():
    model = DummyModel()
    middleware = UQMiddleware(model, UQConfig())
    response = middleware.invoke("prompt", config={"metadata": {"logprobs": True, "top_logprobs": 2, "deterministic": True}})
    assert "uq_result" in response.response_metadata

    async_response = asyncio.run(
        middleware.ainvoke("prompt", config={"metadata": {"logprobs": True, "top_logprobs": 2, "deterministic": True}})
    )
    assert "uq_result" in async_response.response_metadata


def test_langgraph_state_helpers_interrupt_for_blocking_actions():
    response = RiskyToolResponse()
    state = enrich_graph_state({}, response, UQConfig(), {"logprobs": True, "top_logprobs": 2, "deterministic": True})
    assert "uq_result" in state
    assert should_interrupt_before_tool("weather_lookup", state) is True
    assert should_interrupt_before_tool("other_tool", state) is False


class DummyResponsesClient:
    def create(self, **_kwargs):
        return _responses_payload()


class DummyChatCompletionsClient:
    def create(self, **_kwargs):
        return _chat_response()


class DummyBaseClient:
    def __init__(self):
        self.responses = DummyResponsesClient()
        self.chat = type("Chat", (), {"completions": DummyChatCompletionsClient()})()


def test_openai_wrapper_returns_response_result_and_decision():
    wrapped = UQWrappedOpenAI(DummyBaseClient(), UQConfig())
    response_call = wrapped.responses.create(model="gpt-4.1-mini", include=["message.output_text.logprobs"], top_logprobs=2, temperature=0.0, top_p=1.0)
    chat_call = wrapped.chat.completions.create(model="gpt-4o-mini", logprobs=True, top_logprobs=2, temperature=0.0, top_p=1.0)
    assert response_call.result.decision is not None
    assert chat_call.result.decision is not None
    assert response_call.decision.action == response_call.result.action
    assert chat_call.decision.action == chat_call.result.action

