import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from uq_runtime.adapters.fireworks import FireworksAdapter
from uq_runtime.adapters.gemini import GeminiAdapter
from uq_runtime.adapters.litellm import LiteLLMAdapter
from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.adapters.openrouter import OpenRouterAdapter
from uq_runtime.adapters.together import TogetherAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.integrations.langchain_middleware import analyze_after_model_call
from uq_runtime.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.errors import SelectedTokenLogprobsUnavailableError


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(*parts: str) -> dict:
    with (FIXTURES.joinpath(*parts)).open() as handle:
        return json.load(handle)


@pytest.mark.contract
def test_openai_chat_contract_fixture():
    payload = load_fixture("openai", "chat_tool_call.json")
    adapter = OpenAIChatAdapter()
    record = adapter.capture(payload["response"], payload["request_meta"])
    result = Analyzer().analyze_step(record, adapter.capability_report(payload["response"], payload["request_meta"]))
    assert record.structured_blocks[0].type == "tool_call"
    assert result.capability_level.value == "full"


@pytest.mark.contract
def test_openai_responses_contract_fixture():
    payload = load_fixture("openai", "responses_tool_call.json")
    adapter = OpenAIResponsesAdapter()
    record = adapter.capture(payload["response"], payload["request_meta"])
    result = Analyzer().analyze_step(record, adapter.capability_report(payload["response"], payload["request_meta"]))
    assert record.structured_blocks[0].type == "function_call"
    assert result.mode == "canonical"


@pytest.mark.contract
def test_openrouter_contract_fixture_and_missing_logprobs_case():
    payload = load_fixture("openrouter", "chat_tool_call.json")
    adapter = OpenRouterAdapter()
    record = adapter.capture(payload["response"], payload["request_meta"])
    capability = adapter.capability_report(payload["response"], payload["request_meta"])
    result = Analyzer().analyze_step(record, capability)
    assert capability.provider_declared_support is True
    assert result.capability_level.value == "full"

    missing = load_fixture("openrouter", "missing_logprobs.json")
    try:
        Analyzer().analyze_step(adapter.capture(missing["response"], missing["request_meta"]), adapter.capability_report(missing["response"], missing["request_meta"]))
    except SelectedTokenLogprobsUnavailableError:
        pass
    else:
        raise AssertionError("Expected SelectedTokenLogprobsUnavailableError for missing logprobs fixture")


@pytest.mark.contract
def test_litellm_contract_fixture_and_missing_logprobs_case():
    payload = load_fixture("litellm", "chat_tool_call.json")
    adapter = LiteLLMAdapter()
    capability = adapter.capability_report(payload["response"], payload["request_meta"])
    result = Analyzer().analyze_step(adapter.capture(payload["response"], payload["request_meta"]), capability)
    assert capability.provider_declared_support is True
    assert result.capability_level.value == "full"

    missing = load_fixture("litellm", "missing_logprobs.json")
    try:
        Analyzer().analyze_step(adapter.capture(missing["response"], missing["request_meta"]), adapter.capability_report(missing["response"], missing["request_meta"]))
    except SelectedTokenLogprobsUnavailableError:
        pass
    else:
        raise AssertionError("Expected SelectedTokenLogprobsUnavailableError for missing logprobs fixture")


@pytest.mark.contract
def test_gemini_fireworks_together_contract_fixtures():
    gemini = load_fixture("gemini", "generate_content.json")
    gemini_result = Analyzer().analyze_step(
        GeminiAdapter().capture(gemini["response"], gemini["request_meta"]),
        GeminiAdapter().capability_report(gemini["response"], gemini["request_meta"]),
    )
    assert gemini_result.capability_level.value == "full"

    fireworks = load_fixture("fireworks", "chat_completion.json")
    fireworks_result = Analyzer().analyze_step(
        FireworksAdapter().capture(fireworks["response"], fireworks["request_meta"]),
        FireworksAdapter().capability_report(fireworks["response"], fireworks["request_meta"]),
    )
    assert fireworks_result.segments

    together = load_fixture("together", "chat_completion.json")
    together_result = Analyzer().analyze_step(
        TogetherAdapter().capture(together["response"], together["request_meta"]),
        TogetherAdapter().capability_report(together["response"], together["request_meta"]),
    )
    assert together_result.capability_level.value == "full"


@dataclass
class FixtureMessage:
    content: str
    response_metadata: dict
    additional_kwargs: dict


@pytest.mark.contract
def test_langchain_langgraph_and_openai_agents_contract_fixtures():
    langchain_payload = load_fixture("langchain", "message_response.json")
    response = FixtureMessage(
        content=langchain_payload["content"],
        response_metadata=langchain_payload["response_metadata"],
        additional_kwargs=langchain_payload["additional_kwargs"],
    )
    result = analyze_after_model_call(response, UQConfig(), langchain_payload["request_meta"])
    assert result.decision is not None
    assert "uq_result" in response.response_metadata

    langgraph_payload = load_fixture("langgraph", "risky_tool_response.json")
    graph_response = FixtureMessage(
        content=langgraph_payload["content"],
        response_metadata=langgraph_payload["response_metadata"],
        additional_kwargs=langgraph_payload["additional_kwargs"],
    )
    state = enrich_graph_state({}, graph_response, UQConfig(), langgraph_payload["request_meta"])
    assert should_interrupt_before_tool("weather_lookup", state) is True

    agents_payload = load_fixture("openai_agents", "responses_payload.json")
    adapter = OpenAIAgentsAdapter()
    result = Analyzer().analyze_step(
        adapter.capture(agents_payload["response"], agents_payload["request_meta"]),
        adapter.capability_report(agents_payload["response"], agents_payload["request_meta"]),
    )
    assert result.capability_level.value == "full"

