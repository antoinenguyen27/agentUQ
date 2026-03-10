"""OpenAI Chat Completions adapter."""

from __future__ import annotations

from typing import Any

from agentuq.adapters.base import as_dict, block, infer_capability, normalize_top_logprobs, requested_logprobs, requested_topk
from agentuq.schemas.records import CapabilityReport, GenerationRecord


def _flatten_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                parts.append(item.get("text", ""))
        return "".join(parts)
    return ""


def _normalize_chat_logprobs(logprobs_payload: dict[str, Any] | None) -> tuple[list[str], list[float], list[list]]:
    tokens: list[str] = []
    logprobs: list[float] = []
    top_logprobs: list[list] = []
    payload = logprobs_payload or {}
    content_items = payload.get("content") or []
    if content_items:
        for item in content_items:
            tokens.append(item.get("token", ""))
            if item.get("logprob") is not None:
                logprobs.append(float(item["logprob"]))
            top_logprobs.append(normalize_top_logprobs(item.get("top_logprobs")))
        return tokens, logprobs, top_logprobs

    raw_tokens = payload.get("tokens") or []
    raw_logprobs = payload.get("token_logprobs") or []
    raw_top = payload.get("top_logprobs") or []
    for index, token in enumerate(raw_tokens):
        tokens.append(str(token))
        if index < len(raw_logprobs) and raw_logprobs[index] is not None:
            logprobs.append(float(raw_logprobs[index]))
        top_item = raw_top[index] if index < len(raw_top) else None
        if isinstance(top_item, dict):
            top_logprobs.append(
                normalize_top_logprobs(
                    [{"token": top_token, "logprob": top_logprob} for top_token, top_logprob in top_item.items()]
                )
            )
        elif isinstance(top_item, list):
            top_logprobs.append(normalize_top_logprobs(top_item))
        else:
            top_logprobs.append([])
    return tokens, logprobs, top_logprobs


class OpenAIChatAdapter:
    provider = "openai"
    transport = "direct_api"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        data = as_dict(response)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = _flatten_message_content(message.get("content"))
        tokens, logprobs, top_logprobs = _normalize_chat_logprobs(choice.get("logprobs"))
        structured_blocks = []
        tool_calls = message.get("tool_calls") or []
        if content:
            structured_blocks.append(block("output_text", text=content, metadata={"role": "final"}))
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            name = function.get("name")
            arguments = function.get("arguments")
            combined = f"{name or ''}{arguments or ''}"
            structured_blocks.append(
                block(
                    "tool_call",
                    text=combined,
                    name=name,
                    arguments=arguments,
                    metadata={"id": tool_call.get("id"), "token_grounded": False},
                )
            )
        return GenerationRecord(
            provider=self.provider,
            transport=self.transport,
            model=data.get("model") or (request_meta or {}).get("model") or "unknown",
            request_id=data.get("id"),
            temperature=(request_meta or {}).get("temperature"),
            top_p=(request_meta or {}).get("top_p"),
            max_tokens=(request_meta or {}).get("max_tokens"),
            stream=(request_meta or {}).get("stream"),
            step_kind=(request_meta or {}).get("step_kind"),
            raw_text=content,
            selected_tokens=tokens,
            selected_logprobs=logprobs or None,
            top_logprobs=top_logprobs or None,
            structured_blocks=structured_blocks,
            metadata={
                "request_logprobs": requested_logprobs(request_meta),
                "request_topk": requested_topk(request_meta),
                "deterministic": (request_meta or {}).get("deterministic"),
            },
        )

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        record = self.capture(response, request_meta)
        return infer_capability(record, request_meta, declared_support=True)
