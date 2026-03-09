"""OpenAI wrapper surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.results import Decision, UQResult


@dataclass
class WrappedCallResult:
    response: Any
    result: UQResult
    decision: Decision


class _ResponsesProxy:
    def __init__(self, client: Any, analyzer: Analyzer) -> None:
        self._client = client
        self._analyzer = analyzer
        self._adapter = OpenAIResponsesAdapter()

    def create(self, **kwargs: Any) -> WrappedCallResult:
        response = self._client.responses.create(**kwargs)
        request_meta = {
            "model": kwargs.get("model"),
            "temperature": kwargs.get("temperature"),
            "top_p": kwargs.get("top_p"),
            "max_output_tokens": kwargs.get("max_output_tokens"),
            "include": kwargs.get("include"),
            "top_logprobs": kwargs.get("top_logprobs"),
            "deterministic": kwargs.get("temperature") == 0.0 and kwargs.get("top_p") == 1.0,
        }
        record = self._adapter.capture(response, request_meta)
        result = self._analyzer.analyze_step(record, self._adapter.capability_report(response, request_meta))
        return WrappedCallResult(response=response, result=result, decision=result.decision)


class _ChatCompletionsProxy:
    def __init__(self, client: Any, analyzer: Analyzer) -> None:
        self._client = client
        self._analyzer = analyzer
        self._adapter = OpenAIChatAdapter()

    def create(self, **kwargs: Any) -> WrappedCallResult:
        response = self._client.chat.completions.create(**kwargs)
        request_meta = {
            "model": kwargs.get("model"),
            "temperature": kwargs.get("temperature"),
            "top_p": kwargs.get("top_p"),
            "max_tokens": kwargs.get("max_tokens"),
            "logprobs": kwargs.get("logprobs"),
            "top_logprobs": kwargs.get("top_logprobs"),
            "deterministic": kwargs.get("temperature") == 0.0 and kwargs.get("top_p") == 1.0,
        }
        record = self._adapter.capture(response, request_meta)
        result = self._analyzer.analyze_step(record, self._adapter.capability_report(response, request_meta))
        return WrappedCallResult(response=response, result=result, decision=result.decision)


class _ChatProxy:
    def __init__(self, client: Any, analyzer: Analyzer) -> None:
        self.completions = _ChatCompletionsProxy(client, analyzer)


class UQWrappedOpenAI:
    def __init__(self, base_client: Any, uq: UQConfig | None = None) -> None:
        self._client = base_client
        self._analyzer = Analyzer(uq or UQConfig())
        self.responses = _ResponsesProxy(base_client, self._analyzer)
        self.chat = _ChatProxy(base_client, self._analyzer)
