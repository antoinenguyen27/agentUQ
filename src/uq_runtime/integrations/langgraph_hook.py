"""LangGraph-oriented helper functions."""

from __future__ import annotations

from typing import Any

from uq_runtime.integrations.langchain_middleware import analyze_after_model_call, guard_before_tool_execution
from uq_runtime.schemas.config import UQConfig


def enrich_graph_state(state: dict[str, Any], response: Any, config: UQConfig, request_meta: dict | None = None) -> dict[str, Any]:
    result = analyze_after_model_call(response, config, request_meta)
    next_state = dict(state)
    next_state["uq_result"] = result.model_dump(mode="json")
    return next_state


def should_interrupt_before_tool(tool_name: str, state: dict[str, Any]) -> bool:
    uq_result = state.get("uq_result")
    if not uq_result:
        return False
    from uq_runtime.schemas.results import UQResult

    result = UQResult.model_validate(uq_result)
    return guard_before_tool_execution(tool_name, result).value in {
        "ask_user_confirmation",
        "block_execution",
        "retry_step_with_constraints",
    }

