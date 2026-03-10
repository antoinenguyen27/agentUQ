"""Fireworks OpenAI-compatible adapter."""

from __future__ import annotations

from typing import Any

from agentuq.adapters.base import as_dict, infer_capability, normalize_top_logprobs
from agentuq.adapters.openai_chat import OpenAIChatAdapter, _normalize_chat_logprobs
from agentuq.schemas.records import CapabilityReport, GenerationRecord


class FireworksAdapter:
    provider = "fireworks"
    transport = "direct_api"

    def __init__(self) -> None:
        self._delegate = OpenAIChatAdapter()

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        data = as_dict(response)
        record = self._delegate.capture(data, request_meta)
        choice = (data.get("choices") or [{}])[0]
        logprobs_payload = choice.get("logprobs") or {}
        tokens, logprobs, top_logprobs = _normalize_chat_logprobs(logprobs_payload)
        source = None
        if (logprobs_payload or {}).get("content"):
            source = "openai_compatible_content"
        elif (logprobs_payload or {}).get("tokens"):
            source = "legacy_token_arrays"
        if not tokens:
            raw_completion_logprobs = (((data.get("raw_output") or {}).get("completion_logprobs") or {}).get("content")) or []
            tokens = [item.get("token", "") for item in raw_completion_logprobs]
            logprobs = [float(item["logprob"]) for item in raw_completion_logprobs if item.get("logprob") is not None]
            top_logprobs = [normalize_top_logprobs(item.get("top_logprobs")) for item in raw_completion_logprobs]
            if tokens:
                source = "raw_output_completion_logprobs"
        if tokens:
            record.selected_tokens = tokens
            record.selected_logprobs = logprobs or None
            record.top_logprobs = top_logprobs or None
        if source:
            record.metadata["fireworks_logprobs_source"] = source
        record.provider = self.provider
        record.transport = self.transport
        return record

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=True)
