"""LangChain response adapter."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import infer_capability
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


class LangChainAdapter:
    provider = "langchain"
    transport = "langchain"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        metadata = getattr(response, "response_metadata", {}) or {}
        llm_output = getattr(response, "additional_kwargs", {}) or {}
        payload = {
            "id": getattr(response, "id", None),
            "model": metadata.get("model_name") or (request_meta or {}).get("model"),
            "choices": [
                {
                    "message": {
                        "content": getattr(response, "content", ""),
                        "tool_calls": llm_output.get("tool_calls") or [],
                    },
                    "logprobs": metadata.get("logprobs"),
                }
            ],
        }
        record = OpenAIChatAdapter().capture(payload, request_meta)
        record.provider = self.provider
        record.transport = self.transport
        record.metadata["langchain_response_metadata"] = metadata
        return record

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=None)

