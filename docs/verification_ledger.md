---
title: Documentation Verification Ledger
description: External documentation sources currently used to shape AgentUQ adapter behavior and request-helper defaults.
slug: /maintainers/verification-ledger
sidebar_position: 16
---

# Documentation Verification Ledger

This file records the current external docs used to shape AgentUQ integration behavior.

- OpenAI API docs: Responses API logprobs, Chat Completions logprobs, structured outputs, function calling
- OpenAI Agents SDK docs: model settings and tracing-oriented integration points
- LangChain docs: chat model binding and response metadata surfaces
- LangGraph docs: wrapper and interrupt patterns around tool execution
- OpenRouter docs: `provider.require_parameters`, `supported_parameters`, and routing caveats
- LiteLLM docs: OpenAI-compatible params, `drop_params`, and supported-params probing
- Google Gemini docs: `responseLogprobs`, `logprobs`, and `logprobsResult`
- Fireworks docs: OpenAI-compatible `choices[].logprobs.content`, with compatibility fallbacks for legacy token-array payloads
- Together docs: chat/completions logprobs under `choices[].logprobs`

AgentUQ uses these sources for adapter shape decisions and runtime request-helper defaults. When docs are ambiguous or SDK-specific response objects vary, adapters normalize dict-like payloads conservatively and surface capability degradation rather than assuming unsupported fields exist. In particular, OpenAI-family tool calls are treated as structural metadata unless the upstream surface provides explicit token-grounded spans.
