"""OpenAI Chat Completions adapter."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import as_dict, block, infer_capability, normalize_top_logprobs
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


class OpenAIChatAdapter:
    provider = "openai"
    transport = "direct_api"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        data = as_dict(response)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        tokens: list[str] = []
        logprobs: list[float] = []
        top_logprobs: list[list] = []
        logprob_content = ((choice.get("logprobs") or {}).get("content")) or []
        for item in logprob_content:
            tokens.append(item.get("token", ""))
            if item.get("logprob") is not None:
                logprobs.append(float(item["logprob"]))
            top_logprobs.append(normalize_top_logprobs(item.get("top_logprobs")))
        structured_blocks = []
        tool_calls = message.get("tool_calls") or []
        if content:
            structured_blocks.append(block("output_text", text=content, metadata={"role": "final"}))
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            name = function.get("name")
            arguments = function.get("arguments")
            combined = f"{name or ''}{arguments or ''}"
            structured_blocks.append(block("tool_call", text=combined, name=name, arguments=arguments, metadata={"id": tool_call.get("id")}))
        raw_text = content
        if tool_calls:
            parts = [content] if content else []
            for tool_call in tool_calls:
                function = tool_call.get("function") or {}
                parts.append(function.get("name", ""))
                parts.append(function.get("arguments", ""))
            raw_text = "\n".join(part for part in parts if part)
        return GenerationRecord(
            provider=self.provider,
            transport=self.transport,
            model=data.get("model", request_meta.get("model") if request_meta else "unknown"),
            request_id=data.get("id"),
            temperature=(request_meta or {}).get("temperature"),
            top_p=(request_meta or {}).get("top_p"),
            max_tokens=(request_meta or {}).get("max_tokens"),
            stream=(request_meta or {}).get("stream"),
            step_kind=(request_meta or {}).get("step_kind"),
            raw_text=raw_text,
            selected_tokens=tokens,
            selected_logprobs=logprobs or None,
            top_logprobs=top_logprobs or None,
            structured_blocks=structured_blocks,
            metadata={
                "request_logprobs": bool((request_meta or {}).get("logprobs")),
                "request_topk": (request_meta or {}).get("top_logprobs"),
                "deterministic": (request_meta or {}).get("deterministic"),
            },
        )

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        record = self.capture(response, request_meta)
        return infer_capability(record, request_meta, declared_support=True)

