---
title: Integrations
description: Framework integration helpers for LangChain, LangGraph, and other runtime orchestration layers.
slug: /reference/integrations
sidebar_position: 14
---

# Integrations

All exported integration helpers are re-exported from `agentuq.integrations`.

## `UQMiddleware` (`Stable`)

- Import: `from agentuq.integrations import UQMiddleware`
- Signature:
  `UQMiddleware(model, uq: UQConfig | None = None)`
  `invoke(*args, **kwargs) -> Any`
  `ainvoke(*args, **kwargs) -> Any`
- Purpose: wrap a LangChain-style model and attach `uq_result` to `response.response_metadata`
- Intended insertion point: immediately around the model call in LangChain-style workflows
- Returns / output: original framework response with serialized `uq_result` stored in response metadata
- Caveat: this helper depends on what the framework preserved in `response_metadata`; see [Provider and framework capabilities](../concepts/provider_capabilities.md)
- Links: [LangChain quickstart](../quickstarts/langchain.md)

## `analyze_after_model_call` (`Advanced`)

- Import: `from agentuq.integrations import analyze_after_model_call`
- Signature: `analyze_after_model_call(response, config: UQConfig, request_meta: dict | None = None, *, model=None) -> UQResult`
- Purpose: normalize a framework response, analyze it, and attach serialized `uq_result` back onto the response metadata
- Intended insertion point: immediately after a model node or framework model invocation
- Returns / output: `UQResult`
- Caveat: request metadata may be inferred from the model and response metadata when not provided explicitly

## `guard_before_tool_execution` (`Advanced`)

- Import: `from agentuq.integrations import guard_before_tool_execution`
- Signature: `guard_before_tool_execution(tool_name: str, uq_result: UQResult) -> Action`
- Purpose: map a tool name to the segment action for an explicitly grounded tool segment
- Intended insertion point: just before a tool call in frameworks that already hold a `UQResult`
- Returns / output: `Action`
- Caveat: returns `continue` when there is no grounded tool segment for the named tool

## `enrich_graph_state` (`Stable`)

- Import: `from agentuq.integrations import enrich_graph_state`
- Signature: `enrich_graph_state(state: dict[str, Any], response, config: UQConfig, request_meta: dict | None = None) -> dict[str, Any]`
- Purpose: analyze a framework response and store serialized `uq_result` on copied graph state
- Intended insertion point: immediately after a LangGraph model node
- Returns / output: new state dict with `uq_result`
- Caveat: this helper does not itself block tool execution; callers still branch on the stored result or use the narrower boolean helper
- Links: [LangGraph quickstart](../quickstarts/langgraph.md)

## `should_interrupt_before_tool` (`Stable`)

- Import: `from agentuq.integrations import should_interrupt_before_tool`
- Signature: `should_interrupt_before_tool(tool_name: str, state: dict[str, Any]) -> bool`
- Purpose: narrow boolean guard for tool execution from graph state
- Intended insertion point: before a tool node when `uq_result` is already stored on state
- Returns / output: `True` for grounded tool-facing actions that should interrupt, otherwise `False`
- Caveat: this helper is intentionally narrow and depends on explicit grounded tool segments; most OpenAI-compatible tool flows should branch on `result.decision.action` instead
- Links: [LangGraph quickstart](../quickstarts/langgraph.md), [Acting on decisions](../concepts/acting_on_decisions.md)

