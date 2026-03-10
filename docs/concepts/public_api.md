---
title: API Reference
description: Overview page for the split AgentUQ reference documentation, audited against the implemented public surface.
slug: /reference/api
sidebar_position: 9
---

# API Reference

AgentUQ's canonical API reference is now split into focused pages so the docs are usable on the web instead of being one long scroll.

## How to read this section

- `Stable`: intended long-term public surface for normal library use
- `Advanced`: real supported surface, but narrower, more caveat-heavy, or less central to the default integration loop

## Coverage inventory

This reference set is audited against these implemented sources of truth:

- `agentuq.__all__`: `Action`, `Analyzer`, `CapabilityReport`, `Decision`, `GenerationRecord`, `PolicyEngine`, `TolerancePreset`, `UQConfig`, `UQResult`, `print_result_rich`, `render_result`, `render_result_rich`, `resolve_thresholds`
- `agentuq.adapters.__all__`: `FireworksAdapter`, `GeminiAdapter`, `LiteLLMAdapter`, `OpenAIAgentsAdapter`, `OpenAIChatAdapter`, `OpenAIResponsesAdapter`, `OpenRouterAdapter`, `TogetherAdapter`, `model_settings_with_logprobs`, `probe_litellm_capability`, `probe_openrouter_model`
- `agentuq.integrations.__all__`: `UQMiddleware`, `analyze_after_model_call`, `enrich_graph_state`, `guard_before_tool_execution`, `should_interrupt_before_tool`
- `agentuq.schemas.__all__`: `Action`, `CapabilityReport`, `Decision`, `Event`, `GenerationRecord`, `SegmentResult`, `StructuredBlock`, `TolerancePreset`, `TopToken`, `UQConfig`, `UQResult`, `resolve_thresholds`
- additional audited public surfaces: `agentuq.request_params.request_params`, `agentuq.adapters.openai_agents.latest_raw_response`, and public error types in `agentuq.schemas.errors`

## Reference map

- [Root API](../reference/root-api.md): top-level exports from `agentuq`
- [Config models](../reference/config-models.md): `UQConfig`, capability config, thresholds, segmentation, integrations, and custom rules
- [Records and results](../reference/results-and-records.md): `GenerationRecord`, `CapabilityReport`, `UQResult`, `Decision`, segments, events, and enums
- [Adapters](../reference/adapters.md): provider and framework adapters
- [Integrations](../reference/integrations.md): middleware and graph helpers
- [Utilities and errors](../reference/utilities-and-errors.md): advanced helper functions and public error types

## Not covered here

This section does not document internal implementation modules such as segmentation internals, metric helpers, adapter base protocols, rendering display internals, or low-level utility helpers. It focuses on public entrypoints and user-visible models.

## Read alongside the concepts docs

Use [Reading results](reading_results.md), [Policies](policies.md), [Tolerance](tolerance.md), [Canonical vs realized](canonical_vs_realized.md), [Troubleshooting](troubleshooting.md), and [Provider and framework capabilities](provider_capabilities.md) for the deeper behavioral and conceptual explanation behind these interfaces.

