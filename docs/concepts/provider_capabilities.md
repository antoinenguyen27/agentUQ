---
title: Provider And Framework Capabilities
description: Capability expectations and caveats for direct providers, gateways, and framework metadata surfaces.
slug: /concepts/provider-capabilities
sidebar_position: 6
---

# Provider And Framework Capabilities

AgentUQ relies on what the upstream surface actually returns, not what a request parameter merely suggests should be available.

This page summarizes the current behavior of each supported provider or framework surface in the implementation.

## How to read this page

The most important questions are:

- does the surface return selected-token logprobs?
- does it return top-k logprobs?
- does it return structured blocks such as tool calls?
- are tool names or arguments token-grounded, or only structural metadata?

For tier names such as `full` and `selected_only`, see [Capability tiers](capability_tiers.md).

## Direct provider surfaces

| Surface | Status | Selected-token logprobs | Top-k logprobs | Structured blocks | Grounded tool spans | Main caveat |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAI Responses | Stable | Yes, on `output_text` when requested | Yes, when `top_logprobs` is returned | Yes | No, tool/function calls are structural only | Tool-call names/args are not treated as token-grounded unless the upstream surface provides explicit grounding |
| OpenAI Chat Completions | Preview | Yes, when `logprobs=True` | Yes, when `top_logprobs=k` is returned | Yes | No, `tool_calls` are structural only | OpenAI-family tool calls often appear as metadata, not token-grounded spans |
| Gemini | Preview | Yes, via `responseLogprobs=true` and `logprobsResult.chosenCandidates` | Yes, via `topCandidates` when requested | Limited text structure | No | Capability depends on `responseLogprobs`; no selected-token logprobs means no top-k diagnostics either |
| Fireworks | Preview | Yes | Yes | OpenAI-compatible text structure | No | Logprobs may appear in multiple payload shapes; AgentUQ normalizes the supported variants |
| Together | Preview | Yes | Yes | Text only in current normalization | No | Uses token arrays and top-logprob maps rather than OpenAI-style content items |

## OpenAI-compatible gateways

| Surface | Status | Selected-token logprobs | Top-k logprobs | Structured blocks | Grounded tool spans | Main caveat |
| --- | --- | --- | --- | --- | --- | --- |
| OpenRouter | Preview | Depends on route and supported parameters | Depends on route and supported parameters | OpenAI-compatible | No | A request may be accepted even if the routed backend does not return the requested token details |
| LiteLLM | Preview | Depends on upstream provider and param support | Depends on upstream provider and param support | OpenAI-compatible | No | Param dropping can hide unsupported logprob requests unless configured carefully |

For UQ-critical runs:

- OpenRouter: prefer `provider.require_parameters=true`
- LiteLLM: prefer `drop_params=False` and inspect `supported_openai_params`

## Framework surfaces

| Surface | Status | Selected-token logprobs | Top-k logprobs | Structured blocks | Grounded tool spans | Main caveat |
| --- | --- | --- | --- | --- | --- | --- |
| LangChain | Preview | Inherits underlying provider if exposed in `response_metadata` | Inherits underlying provider if exposed | Yes, normalized from provider response and tool-call metadata | Usually no | Capability is inferred from what the framework preserved, not from the original provider promise |
| LangGraph | Preview | Same as LangChain model nodes | Same as LangChain model nodes | Same as LangChain | Usually no | Best used by attaching `uq_result` after model nodes and gating before tool nodes |
| OpenAI Agents SDK helpers | Preview | Inherits OpenAI Responses behavior | Inherits OpenAI Responses behavior | Yes | Usually no | Best used as a thin integration layer around model results and traces, not as a fork of the runtime |

## What "no grounded tool spans" means

Many provider and framework surfaces return tool calls structurally:

- tool name
- argument string
- call ID

That is still useful for workflow control, but it is not the same as token-grounded tool uncertainty. AgentUQ does **not** synthesize token-grounded `tool_name` or `tool_argument_leaf` spans by substring-matching assistant prose.

Instead:

- structural metadata is recorded
- text logprobs are scored where they exist
- grounded tool segments are emitted only when the runtime has explicit token/character grounding for them

## Practical expectations by surface

### Best current surfaces for text-level runtime UQ

- OpenAI Responses
- OpenAI Chat Completions (`Preview`)
- Fireworks (`Preview`)
- Gemini (`Preview`)
- Together (`Preview`)

These surfaces are the most straightforward when you mainly care about emitted text spans such as prose, SQL, code, browser DSL, and shell-like snippets.

### Best current surfaces for framework integration

- LangChain middleware usage (`Preview`)
- LangGraph state enrichment and pre-tool interruption (`Preview`)

These are strongest when you want AgentUQ to travel with the existing framework object model rather than building records manually.

### Most important caveat to remember

Even when a surface supports structured tool calls, the tool call is often **not** token-grounded. That means:

- structural tool metadata can still be used for orchestration
- but span-level uncertainty is only available on emitted text or explicitly grounded spans

## Capability honesty rules

AgentUQ determines capability in this order:

1. provider-declared support when available
2. requested parameters
3. observed response payload

This is why capability reporting can downgrade a step even when the upstream route accepted the request.

For examples of request settings by provider, see the provider quickstarts in [`docs/quickstarts`](../quickstarts).
