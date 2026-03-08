"""LangChain and LangGraph wrapper helpers."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.langchain import LangChainAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.results import Action, UQResult


def analyze_after_model_call(response: Any, config: UQConfig, request_meta: dict | None = None) -> UQResult:
    adapter = LangChainAdapter()
    analyzer = Analyzer(config)
    record = adapter.capture(response, request_meta)
    result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
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
        analyze_after_model_call(response, self.uq, request_meta)
        return response

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        response = await self.model.ainvoke(*args, **kwargs)
        request_meta = kwargs.get("config", {}).get("metadata", {}) if kwargs.get("config") else {}
        analyze_after_model_call(response, self.uq, request_meta)
        return response
