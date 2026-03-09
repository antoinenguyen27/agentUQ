"""OpenAI Responses API adapter."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import as_dict, block, infer_capability, normalize_top_logprobs, requested_logprobs, requested_topk
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


class OpenAIResponsesAdapter:
    provider = "openai"
    transport = "direct_api"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        data = as_dict(response)
        output_items = data.get("output") or []
        tokens: list[str] = []
        logprobs: list[float] = []
        top_logprobs: list[list] = []
        blocks = []
        raw_text_parts: list[str] = []
        char_cursor = 0

        for item in output_items:
            item_type = item.get("type")
            if item_type == "message":
                for content in item.get("content") or []:
                    if content.get("type") in {"output_text", "text"}:
                        text = content.get("text", "")
                        if raw_text_parts and text:
                            raw_text_parts.append("\n")
                            char_cursor += 1
                        blocks.append(block("output_text", text=text, char_start=char_cursor, char_end=char_cursor + len(text), metadata={"role": "final"}))
                        raw_text_parts.append(text)
                        for token_info in content.get("logprobs") or []:
                            tokens.append(token_info.get("token", ""))
                            if token_info.get("logprob") is not None:
                                logprobs.append(float(token_info["logprob"]))
                            top_logprobs.append(normalize_top_logprobs(token_info.get("top_logprobs")))
                        char_cursor += len(text)
            if item_type in {"function_call", "tool_call"}:
                name = item.get("name")
                arguments = item.get("arguments") or item.get("input")
                combined = f"{name or ''}{arguments or ''}"
                blocks.append(
                    block(
                        "function_call",
                        text=combined,
                        name=name,
                        arguments=arguments,
                        metadata={"call_id": item.get("call_id"), "token_grounded": False},
                    )
                )
        raw_text = "".join(raw_text_parts)
        return GenerationRecord(
            provider=self.provider,
            transport=self.transport,
            model=data.get("model") or (request_meta or {}).get("model") or "unknown",
            request_id=data.get("id"),
            temperature=(request_meta or {}).get("temperature"),
            top_p=(request_meta or {}).get("top_p"),
            max_tokens=(request_meta or {}).get("max_output_tokens"),
            stream=(request_meta or {}).get("stream"),
            step_kind=(request_meta or {}).get("step_kind"),
            raw_text=raw_text,
            selected_tokens=tokens,
            selected_logprobs=logprobs or None,
            top_logprobs=top_logprobs or None,
            structured_blocks=blocks,
            metadata={
                "request_logprobs": requested_logprobs(request_meta),
                "request_topk": requested_topk(request_meta),
                "deterministic": (request_meta or {}).get("deterministic"),
            },
        )

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        record = self.capture(response, request_meta)
        return infer_capability(record, request_meta, declared_support=True)
