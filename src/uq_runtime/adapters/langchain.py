"""LangChain response adapter."""

from __future__ import annotations

import json
from typing import Any

from uq_runtime.adapters.base import as_dict
from uq_runtime.adapters.base import infer_capability
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


def _normalize_langchain_tool_calls(tool_calls: list[Any] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for call in tool_calls or []:
        call_data = as_dict(call)
        if not isinstance(call_data, dict):
            continue
        if isinstance(call_data.get("function"), dict):
            normalized.append(call_data)
            continue
        name = call_data.get("name")
        if not name:
            continue
        args = call_data.get("args")
        if isinstance(args, str):
            arguments = args
        else:
            arguments = json.dumps(as_dict(args) if args is not None else {}, separators=(",", ":"), sort_keys=True)
        normalized.append(
            {
                "id": call_data.get("id"),
                "function": {
                    "name": name,
                    "arguments": arguments,
                },
            }
        )
    return normalized


class LangChainAdapter:
    provider = "langchain"
    transport = "langchain"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        metadata = getattr(response, "response_metadata", {}) or {}
        llm_output = getattr(response, "additional_kwargs", {}) or {}
        tool_calls = _normalize_langchain_tool_calls(getattr(response, "tool_calls", None))
        if not tool_calls:
            tool_calls = _normalize_langchain_tool_calls(llm_output.get("tool_calls"))
        payload = {
            "id": getattr(response, "id", None),
            "model": metadata.get("model_name") or (request_meta or {}).get("model"),
            "choices": [
                {
                    "message": {
                        "content": getattr(response, "content", ""),
                        "tool_calls": tool_calls,
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
