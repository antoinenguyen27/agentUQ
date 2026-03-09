from __future__ import annotations

import os

import pytest

from uq_runtime.integrations.langchain_middleware import UQMiddleware, analyze_after_model_call
from uq_runtime.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from uq_runtime.schemas.config import UQConfig
from tests.live.helpers import require_live_env


pytestmark = pytest.mark.live


@pytest.mark.live
def test_live_langchain_wrapper_smoke():
    require_live_env("OPENAI_API_KEY")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        pytest.skip("Install langchain-openai to run LangChain live smoke tests.")
    model = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("AGENTUQ_LANGCHAIN_MODEL", "gpt-4o-mini"),
        temperature=0.0,
        top_p=1.0,
    ).bind(logprobs=True, top_logprobs=2)
    wrapped = UQMiddleware(model, UQConfig())
    response = wrapped.invoke("Return the single word Paris.")
    assert response.response_metadata.get("logprobs")
    assert "uq_result" in response.response_metadata


@pytest.mark.live
def test_live_langgraph_hook_smoke():
    require_live_env("OPENAI_API_KEY")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        pytest.skip("Install langchain-openai to run LangGraph-style live smoke tests.")
    model = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("AGENTUQ_LANGGRAPH_MODEL", "gpt-4o-mini"),
        temperature=0.0,
        top_p=1.0,
    ).bind(logprobs=True, top_logprobs=2)
    response = model.invoke("Return the single word Paris.")
    assert response.response_metadata.get("logprobs")
    result = analyze_after_model_call(response, UQConfig(), {"logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True})
    state = enrich_graph_state({}, response, UQConfig(), {"logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True})
    assert result.capability_level.value != "none"
    assert result.decision is not None
    assert "uq_result" in state
    assert should_interrupt_before_tool("weather_lookup", state) is False
