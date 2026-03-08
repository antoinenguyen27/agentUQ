"""OpenRouter adapter."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import as_dict, infer_capability
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


def probe_openrouter_model(model: str, supported_parameters: list[str] | None = None) -> dict[str, Any]:
    parameters = supported_parameters or []
    return {
        "model": model,
        "supported_parameters": parameters,
        "supports_logprobs": "logprobs" in parameters,
        "supports_top_logprobs": "top_logprobs" in parameters,
    }


class OpenRouterAdapter:
    provider = "openrouter"
    transport = "openrouter"

    @classmethod
    def from_response(cls, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        return cls().capture(response, request_meta)

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        record = OpenAIChatAdapter().capture(as_dict(response), request_meta)
        record.provider = self.provider
        record.transport = self.transport
        if request_meta:
            record.metadata["provider_require_parameters"] = (request_meta.get("provider") or {}).get("require_parameters")
            record.metadata["route"] = request_meta.get("route")
        return record

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        declared = None
        if request_meta and request_meta.get("supported_parameters") is not None:
            declared = "logprobs" in request_meta["supported_parameters"]
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=declared)

