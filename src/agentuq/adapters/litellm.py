"""LiteLLM adapter and probe helpers."""

from __future__ import annotations

from typing import Any

from agentuq.adapters.base import as_dict, infer_capability
from agentuq.adapters.openai_chat import OpenAIChatAdapter
from agentuq.schemas.records import CapabilityReport, GenerationRecord


def probe_litellm_capability(model: str, provider: str | None = None, supported_openai_params: list[str] | None = None) -> dict[str, Any]:
    supported = set(supported_openai_params or [])
    return {
        "model": model,
        "provider": provider,
        "supports_logprobs": "logprobs" in supported,
        "supports_top_logprobs": "top_logprobs" in supported,
        "supported_openai_params": sorted(supported),
    }


class LiteLLMAdapter:
    provider = "litellm"
    transport = "litellm"

    def __init__(self) -> None:
        self._delegate = OpenAIChatAdapter()

    @classmethod
    def from_response(cls, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        return cls().capture(response, request_meta)

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        record = self._delegate.capture(as_dict(response), request_meta)
        record.provider = self.provider
        record.transport = self.transport
        if request_meta:
            record.metadata["drop_params"] = request_meta.get("drop_params")
            record.metadata["supported_openai_params"] = request_meta.get("supported_openai_params")
        return record

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        declared_support = None
        if request_meta and request_meta.get("supported_openai_params") is not None:
            params = set(request_meta["supported_openai_params"])
            declared_support = "logprobs" in params
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=declared_support)

