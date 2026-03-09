"""Adapter utilities."""

from __future__ import annotations

from typing import Any, Protocol

from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken


class BaseAdapter(Protocol):
    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        ...

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        ...


def as_dict(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "__dict__"):
        return {
            key: as_dict(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    if isinstance(value, list):
        return [as_dict(item) for item in value]
    return value


def requested_logprobs(request_meta: dict[str, Any] | None = None) -> bool:
    request_meta = request_meta or {}
    include = request_meta.get("include") or request_meta.get("response_include") or []
    return bool(
        request_meta.get("logprobs")
        or request_meta.get("responseLogprobs")
        or request_meta.get("include_output_text_logprobs")
        or "message.output_text.logprobs" in include
    )


def requested_topk(request_meta: dict[str, Any] | None = None) -> int | None:
    request_meta = request_meta or {}
    if request_meta.get("top_logprobs") is not None:
        return int(request_meta["top_logprobs"])
    logprobs_value = request_meta.get("logprobs")
    if isinstance(logprobs_value, int) and not isinstance(logprobs_value, bool):
        return logprobs_value
    if request_meta.get("responseLogprobs"):
        gemini_topk = request_meta.get("logprobs")
        if isinstance(gemini_topk, int) and not isinstance(gemini_topk, bool):
            return gemini_topk
    return request_meta.get("logprobs_k")


def infer_capability(record: GenerationRecord, request_meta: dict | None = None, declared_support: bool | None = None) -> CapabilityReport:
    request_meta = request_meta or {}
    topk_k = len(record.top_logprobs[0]) if record.top_logprobs and record.top_logprobs[0] else None
    return CapabilityReport(
        selected_token_logprobs=bool(record.selected_logprobs),
        topk_logprobs=bool(record.top_logprobs),
        topk_k=topk_k,
        structured_blocks=bool(record.structured_blocks),
        function_call_structure=any(block.type in {"tool_call", "function_call"} for block in record.structured_blocks),
        provider_declared_support=declared_support,
        request_attempted_logprobs=requested_logprobs(request_meta),
        request_attempted_topk=requested_topk(request_meta),
        degraded_reason=request_meta.get("degraded_reason"),
    )


def normalize_top_logprobs(items: list[dict[str, Any]] | None) -> list[TopToken]:
    if not items:
        return []
    normalized: list[TopToken] = []
    for item in items:
        token = item.get("token") or item.get("text")
        logprob = item.get("logprob")
        if token is None or logprob is None:
            continue
        normalized.append(TopToken(token=str(token), logprob=float(logprob)))
    return normalized


def block(type_: str, text: str | None = None, **kwargs: Any) -> StructuredBlock:
    return StructuredBlock(type=type_, text=text, **kwargs)
