"""LangChain and LangGraph wrapper helpers."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import as_dict
from uq_runtime.adapters.langchain import LangChainAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.results import Action, UQResult


def _setdefault_if_present(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None and key not in target:
        target[key] = value


def _update_request_meta_from_mapping(target: dict[str, Any], value: Any) -> None:
    data = as_dict(value)
    if not isinstance(data, dict):
        return
    _setdefault_if_present(target, "model", data.get("model"))
    _setdefault_if_present(target, "model", data.get("model_name"))
    if isinstance(data.get("logprobs"), bool) or (isinstance(data.get("logprobs"), int) and not isinstance(data.get("logprobs"), bool)):
        _setdefault_if_present(target, "logprobs", data.get("logprobs"))
    if isinstance(data.get("top_logprobs"), int):
        _setdefault_if_present(target, "top_logprobs", data.get("top_logprobs"))
    if isinstance(data.get("temperature"), (int, float)):
        _setdefault_if_present(target, "temperature", float(data.get("temperature")))
    if isinstance(data.get("top_p"), (int, float)):
        _setdefault_if_present(target, "top_p", float(data.get("top_p")))
    if isinstance(data.get("deterministic"), bool):
        _setdefault_if_present(target, "deterministic", data.get("deterministic"))
    if isinstance(data.get("include"), list):
        _setdefault_if_present(target, "include", data.get("include"))
    if isinstance(data.get("response_include"), list):
        _setdefault_if_present(target, "response_include", data.get("response_include"))
    nested = data.get("model_kwargs")
    if isinstance(nested, dict):
        _update_request_meta_from_mapping(target, nested)


def _update_request_meta_from_model(target: dict[str, Any], model: Any, seen: set[int] | None = None) -> None:
    if model is None:
        return
    seen = seen or set()
    model_id = id(model)
    if model_id in seen:
        return
    seen.add(model_id)
    _update_request_meta_from_mapping(target, model)
    direct_attrs = {
        "model": getattr(model, "model", None),
        "model_name": getattr(model, "model_name", None),
        "logprobs": getattr(model, "logprobs", None),
        "top_logprobs": getattr(model, "top_logprobs", None),
        "temperature": getattr(model, "temperature", None),
        "top_p": getattr(model, "top_p", None),
        "deterministic": getattr(model, "deterministic", None),
        "include": getattr(model, "include", None),
        "response_include": getattr(model, "response_include", None),
    }
    _update_request_meta_from_mapping(target, direct_attrs)
    for attr in ("kwargs", "model_kwargs", "default_kwargs"):
        nested = getattr(model, attr, None)
        if isinstance(nested, dict):
            _update_request_meta_from_mapping(target, nested)
    bound = getattr(model, "bound", None)
    if bound is not None:
        _update_request_meta_from_model(target, bound, seen)


def _infer_topk_from_logprobs_payload(logprobs_payload: Any) -> int | None:
    payload = as_dict(logprobs_payload)
    if not isinstance(payload, dict):
        return None
    content = payload.get("content") or []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("top_logprobs"), list):
            return len(item["top_logprobs"])
    raw_top = payload.get("top_logprobs") or []
    if raw_top:
        first = raw_top[0]
        if isinstance(first, dict):
            return len(first)
        if isinstance(first, list):
            return len(first)
    return None


def resolve_langchain_request_meta(response: Any, request_meta: dict | None = None, model: Any | None = None) -> dict[str, Any]:
    resolved: dict[str, Any] = dict(request_meta or {})
    _update_request_meta_from_model(resolved, model)

    response_metadata = as_dict(getattr(response, "response_metadata", {}) or {})
    if isinstance(response_metadata, dict):
        _setdefault_if_present(resolved, "model", response_metadata.get("model_name"))
        if "logprobs" not in resolved and response_metadata.get("logprobs") is not None:
            resolved["logprobs"] = True
        if "top_logprobs" not in resolved:
            inferred_topk = _infer_topk_from_logprobs_payload(response_metadata.get("logprobs"))
            if inferred_topk is not None:
                resolved["top_logprobs"] = inferred_topk

    if "deterministic" not in resolved and resolved.get("temperature") is not None and resolved.get("top_p") is not None:
        resolved["deterministic"] = resolved["temperature"] == 0.0 and resolved["top_p"] == 1.0
    return resolved


def analyze_after_model_call(
    response: Any,
    config: UQConfig,
    request_meta: dict | None = None,
    *,
    model: Any | None = None,
) -> UQResult:
    adapter = LangChainAdapter()
    analyzer = Analyzer(config)
    resolved_request_meta = resolve_langchain_request_meta(response, request_meta, model=model)
    record = adapter.capture(response, resolved_request_meta)
    result = analyzer.analyze_step(record, adapter.capability_report(response, resolved_request_meta))
    response.response_metadata = getattr(response, "response_metadata", {}) or {}
    response.response_metadata["uq_result"] = result.model_dump(mode="json")
    return result


def guard_before_tool_execution(tool_name: str, uq_result: UQResult) -> Action:
    segment_actions = uq_result.decision.segment_actions if uq_result.decision else {}
    for segment in uq_result.segments:
        if segment.metadata.get("tool_name") == tool_name and segment.id in segment_actions:
            return segment_actions[segment.id]
    return Action.CONTINUE


class UQMiddleware:
    def __init__(self, model: Any, uq: UQConfig | None = None) -> None:
        self.model = model
        self.uq = uq or UQConfig()

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        response = self.model.invoke(*args, **kwargs)
        request_meta = kwargs.get("config", {}).get("metadata", {}) if kwargs.get("config") else {}
        analyze_after_model_call(response, self.uq, request_meta, model=self.model)
        return response

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        response = await self.model.ainvoke(*args, **kwargs)
        request_meta = kwargs.get("config", {}).get("metadata", {}) if kwargs.get("config") else {}
        analyze_after_model_call(response, self.uq, request_meta, model=self.model)
        return response
