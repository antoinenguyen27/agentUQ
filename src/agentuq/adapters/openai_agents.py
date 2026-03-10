"""Helpers for OpenAI Agents SDK results."""

from __future__ import annotations

from typing import Any

from agentuq.adapters.base import as_dict
from agentuq.adapters.openai_responses import OpenAIResponsesAdapter
from agentuq.schemas.records import CapabilityReport, GenerationRecord


def model_settings_with_logprobs(*, top_logprobs: int = 5, include_output_text_logprobs: bool = True, **kwargs: Any) -> dict[str, Any]:
    settings = dict(kwargs)
    settings.setdefault("top_logprobs", top_logprobs)
    if include_output_text_logprobs:
        settings.setdefault("response_include", ["message.output_text.logprobs"])
    return settings


def latest_raw_response(run_result: Any) -> Any:
    raw_responses = getattr(run_result, "raw_responses", None) or []
    if raw_responses:
        return raw_responses[-1]
    raise ValueError(
        "OpenAI Agents run result did not expose raw_responses; AgentUQ requires the raw Responses object for analysis."
    )


class OpenAIAgentsAdapter:
    def __init__(self) -> None:
        self._delegate = OpenAIResponsesAdapter()

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        return self._delegate.capture(as_dict(response), request_meta)

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        return self._delegate.capability_report(as_dict(response), request_meta)
