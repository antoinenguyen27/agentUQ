from __future__ import annotations

import os

import pytest

from uq_runtime.adapters.fireworks import FireworksAdapter
from uq_runtime.adapters.gemini import GeminiAdapter
from uq_runtime.adapters.litellm import LiteLLMAdapter
from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter, model_settings_with_logprobs
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.adapters.openrouter import OpenRouterAdapter
from uq_runtime.adapters.together import TogetherAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from tests.live.helpers import assert_live_result, require_live_env


pytestmark = pytest.mark.live


def _openai_client(base_url: str | None = None):
    require_live_env("OPENAI_API_KEY")
    from openai import OpenAI

    kwargs = {"api_key": os.getenv("OPENAI_API_KEY")}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


@pytest.mark.live
def test_live_openai_responses_smoke():
    require_live_env("OPENAI_API_KEY")
    client = _openai_client()
    response = client.responses.create(
        model=os.getenv("AGENTUQ_OPENAI_RESPONSES_MODEL", "gpt-4.1-mini"),
        input="Return a weather_lookup tool call for Paris.",
        tools=[{
            "type": "function",
            "name": "weather_lookup",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        }],
        include=["message.output_text.logprobs"],
        top_logprobs=2,
        temperature=0.0,
        top_p=1.0,
    )
    request_meta = {"include_output_text_logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True}
    adapter = OpenAIResponsesAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_openai_chat_smoke():
    require_live_env("OPENAI_API_KEY")
    client = _openai_client()
    response = client.chat.completions.create(
        model=os.getenv("AGENTUQ_OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": "Return a short answer: Paris."}],
        logprobs=True,
        top_logprobs=2,
        temperature=0.0,
        top_p=1.0,
    )
    request_meta = {"logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True}
    adapter = OpenAIChatAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_openrouter_smoke():
    require_live_env("OPENROUTER_API_KEY")
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("AGENTUQ_OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        messages=[{"role": "user", "content": "Return a short answer: Paris."}],
        logprobs=True,
        top_logprobs=2,
        provider={"require_parameters": True},
        temperature=0.0,
        top_p=1.0,
    )
    request_meta = {
        "logprobs": True,
        "top_logprobs": 2,
        "provider": {"require_parameters": True},
        "temperature": 0.0,
        "top_p": 1.0,
        "deterministic": True,
    }
    adapter = OpenRouterAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_litellm_smoke():
    require_live_env("OPENAI_API_KEY")
    from litellm import completion

    model = os.getenv("AGENTUQ_LITELLM_MODEL", "openai/gpt-4o-mini")
    response = completion(
        model=model,
        messages=[{"role": "user", "content": "Return a short answer: Paris."}],
        logprobs=True,
        top_logprobs=2,
        drop_params=False,
        temperature=0.0,
        top_p=1.0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    request_meta = {"model": model, "logprobs": True, "top_logprobs": 2, "drop_params": False, "temperature": 0.0, "top_p": 1.0, "deterministic": True}
    adapter = LiteLLMAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_gemini_smoke():
    require_live_env("GEMINI_API_KEY")
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=os.getenv("AGENTUQ_GEMINI_MODEL", "gemini-2.5-flash"),
        contents="Return the single word Paris.",
        config={"responseLogprobs": True, "logprobs": 2, "temperature": 0.0, "topP": 1.0},
    )
    request_meta = {"responseLogprobs": True, "logprobs": 2, "temperature": 0.0, "topP": 1.0, "deterministic": True}
    adapter = GeminiAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_fireworks_smoke():
    require_live_env("FIREWORKS_API_KEY")
    from openai import OpenAI

    client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key=os.getenv("FIREWORKS_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("AGENTUQ_FIREWORKS_MODEL", "accounts/fireworks/models/llama-v3p1-8b-instruct"),
        messages=[{"role": "user", "content": "Return the single word Paris."}],
        logprobs=True,
        top_logprobs=2,
        temperature=0.0,
        top_p=1.0,
    )
    request_meta = {"logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True}
    adapter = FireworksAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_together_smoke():
    require_live_env("TOGETHER_API_KEY")
    from together import Together

    client = Together(api_key=os.getenv("TOGETHER_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("AGENTUQ_TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
        messages=[{"role": "user", "content": "Return the single word Paris."}],
        logprobs=2,
        temperature=0.2,
        top_p=1.0,
    )
    request_meta = {"logprobs": 2, "temperature": 0.2, "top_p": 1.0, "deterministic": False}
    adapter = TogetherAdapter()
    result = Analyzer(UQConfig(mode="realized")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)


@pytest.mark.live
def test_live_openai_agents_helper_settings_shape():
    require_live_env("OPENAI_API_KEY")
    settings = model_settings_with_logprobs(top_logprobs=2)
    assert settings["top_logprobs"] == 2
    assert settings["include"] == ["message.output_text.logprobs"]

    client = _openai_client()
    response = client.responses.create(
        model=os.getenv("AGENTUQ_OPENAI_AGENTS_MODEL", "gpt-4.1-mini"),
        input="Return a weather_lookup tool call for Paris.",
        tools=[{
            "type": "function",
            "name": "weather_lookup",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        }],
        include=settings["include"],
        top_logprobs=settings["top_logprobs"],
        temperature=0.0,
        top_p=1.0,
    )
    request_meta = {"include_output_text_logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True}
    adapter = OpenAIAgentsAdapter()
    result = Analyzer(UQConfig(mode="auto")).analyze_step(adapter.capture(response, request_meta), adapter.capability_report(response, request_meta))
    assert_live_result(result)

