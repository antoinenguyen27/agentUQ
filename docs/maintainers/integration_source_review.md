---
title: Integration Source Review
description: Process for reviewing upstream provider and framework docs when AgentUQ adapters or request-helper defaults change.
slug: /maintainers/integration-source-review
sidebar_position: 9
---

# Integration Source Review

Use this process when a maintainer change depends on upstream provider or framework documentation.

## Purpose

Keep adapter behavior, capability detection, and request-helper defaults aligned with documented upstream behavior.

## When review is required

- adding a new provider, gateway, or framework integration
- changing adapter field mapping or capability detection
- changing request-helper defaults or supported-parameter handling
- investigating upstream API or SDK drift

## Approved source types

- official provider or framework API documentation
- official SDK documentation
- official release notes or migration guides when behavior changed

Prefer documented behavior over examples or community guidance when deciding whether a capability is supported.

## Review process

1. Identify the upstream docs that define the relevant request parameters, response shape, capability flags, and tool or structured-output behavior.
2. Update adapters and request helpers only for behavior that is documented or validated by fixtures or live smoke tests.
3. When upstream behavior is ambiguous, treat the capability as unsupported or degraded rather than assuming it exists.
4. Add or update unit, contract, or live tests when adapter behavior changes.
5. Update user-facing docs when the supported behavior or integration status changes.

## Current source coverage

- OpenAI API docs: Responses API logprobs, Chat Completions logprobs, structured outputs, function calling
- OpenAI Agents SDK docs: model settings and tracing-oriented integration points
- LangChain docs: chat model binding and response metadata surfaces
- LangGraph docs: wrapper and interrupt patterns around tool execution
- OpenRouter docs: `provider.require_parameters`, `supported_parameters`, and routing caveats
- LiteLLM docs: OpenAI-compatible params, `drop_params`, and supported-params probing
- Google Gemini docs: `responseLogprobs`, `logprobs`, and `logprobsResult`
- Fireworks docs: OpenAI-compatible `choices[].logprobs.content`, with compatibility fallbacks for legacy token-array payloads
- Together docs: chat/completions logprobs under `choices[].logprobs`

## Conservative-default rule

When upstream docs or SDK response objects do not clearly guarantee a field, AgentUQ should behave conservatively. For OpenAI-family surfaces, treat tool calls as structural metadata unless the upstream surface exposes explicit token-grounded spans.
