---
title: Adapters
description: Provider and framework adapter classes that normalize upstream payloads into AgentUQ records and capability reports.
slug: /reference/adapters
sidebar_position: 13
---

# Adapters

All adapter classes are re-exported from `agentuq.adapters`.

**Integration status:** `OpenAIResponsesAdapter` is `Stable`. Every other adapter or integration helper on this page is `Preview`.

## `OpenAIResponsesAdapter` (`Stable`)

- Import: `from agentuq.adapters import OpenAIResponsesAdapter`
- Signature:
  `OpenAIResponsesAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize OpenAI Responses API payloads into `GenerationRecord`
- Required / expected input shape: Responses-style objects or dict-like payloads with `output[]`, `message` items, and requested `message.output_text.logprobs`
- Returns / output: normalized text blocks, tokens, logprobs, and structural function/tool call blocks
- Caveat: tool/function call items are captured structurally; token-grounded scoring is limited to message text
- Links: [OpenAI quickstart](../quickstarts/openai.md)

## `OpenAIChatAdapter` (`Preview`)

- Import: `from agentuq.adapters import OpenAIChatAdapter`
- Signature:
  `OpenAIChatAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize OpenAI Chat Completions payloads
- Required / expected input shape: chat completion responses with message content and `choices[0].logprobs.content` when requested
- Returns / output: flattened message text, logprob-aligned tokens, and structural tool call metadata
- Caveat: OpenAI-family `tool_calls` are structural only unless the upstream surface provides explicit grounding
- Links: [OpenAI quickstart](../quickstarts/openai.md)

## `OpenRouterAdapter` (`Preview`)

- Import: `from agentuq.adapters import OpenRouterAdapter`
- Signature:
  `OpenRouterAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize OpenRouter's OpenAI-compatible chat payloads while preserving routed-capability reporting
- Required / expected input shape: OpenAI-compatible chat responses plus request metadata describing requested logprob parameters
- Returns / output: `GenerationRecord` and capability reporting that reflects actual returned capability
- Caveat: a request may be accepted even when the routed backend does not return the requested token details; prefer `provider.require_parameters=true`
- Links: [OpenRouter quickstart](../quickstarts/openrouter.md), [Provider and framework capabilities](../concepts/provider_capabilities.md)

## `LiteLLMAdapter` (`Preview`)

- Import: `from agentuq.adapters import LiteLLMAdapter`
- Signature:
  `LiteLLMAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize LiteLLM responses while preserving upstream capability signals
- Required / expected input shape: `litellm.completion(...)` style responses or dict-like equivalents
- Returns / output: `GenerationRecord`, capability report, and optional convenience `from_response(...)` classmethod behavior
- Caveat: silent parameter dropping can hide unsupported logprob requests; prefer `drop_params=False`
- Links: [LiteLLM quickstart](../quickstarts/litellm.md)

## `GeminiAdapter` (`Preview`)

- Import: `from agentuq.adapters import GeminiAdapter`
- Signature:
  `GeminiAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize Gemini `generate_content` responses
- Required / expected input shape: payloads with `responseLogprobs`, chosen candidates, and optional top candidates when requested
- Returns / output: selected tokens, selected-token logprobs, top candidates, and normalized text blocks
- Caveat: Gemini uses `topP` rather than `top_p` in request metadata, and no chosen-token logprobs means no top-k diagnostics
- Links: [Gemini quickstart](../quickstarts/gemini.md)

## `FireworksAdapter` (`Preview`)

- Import: `from agentuq.adapters import FireworksAdapter`
- Signature:
  `FireworksAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize Fireworks chat completions
- Required / expected input shape: OpenAI-compatible chat payloads or older Fireworks logprob variants
- Returns / output: normalized record and capability report
- Caveat: prefers `choices[0].logprobs.content`, but falls back to older token-array variants when needed
- Links: [Fireworks quickstart](../quickstarts/fireworks.md)

## `TogetherAdapter` (`Preview`)

- Import: `from agentuq.adapters import TogetherAdapter`
- Signature:
  `TogetherAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: normalize Together chat completions
- Required / expected input shape: `choices[0].logprobs` token arrays and top-logprob maps
- Returns / output: normalized text, tokens, logprobs, and capability report
- Caveat: Together requests `logprobs=k` rather than separate `top_logprobs`
- Links: [Together quickstart](../quickstarts/together.md)

## `OpenAIAgentsAdapter` (`Preview`)

- Import: `from agentuq.adapters import OpenAIAgentsAdapter`
- Signature:
  `OpenAIAgentsAdapter()`
  `capture(response, request_meta=None) -> GenerationRecord`
  `capability_report(response, request_meta=None) -> CapabilityReport`
- Purpose: adapt OpenAI Agents SDK raw Responses objects through the Responses normalization path
- Required / expected input shape: raw Responses payloads exposed by the Agents SDK, not the higher-level run result wrapper itself
- Returns / output: same normalized record/capability shape as the Responses adapter
- Caveat: this helper assumes the SDK still exposes raw Responses payloads for analysis
- Links: [OpenAI Agents quickstart](../quickstarts/openai_agents.md)

## `model_settings_with_logprobs` (`Preview`)

- Import: `from agentuq.adapters import model_settings_with_logprobs`
- Signature: `model_settings_with_logprobs(*, top_logprobs=5, include_output_text_logprobs=True, **kwargs) -> dict[str, Any]`
- Purpose: produce an Agents SDK `ModelSettings` kwargs dict that requests output-text logprobs
- Key parameters: `top_logprobs`, `include_output_text_logprobs`, plus passthrough keyword args such as `temperature` and `top_p`
- Returns / output: plain dictionary suitable for `ModelSettings(**settings)`
- Caveat: this helper is specific to the OpenAI Agents SDK `ModelSettings` surface, not raw `OpenAI().responses.create(...)`

## `latest_raw_response` (`Preview`)

- Import: `from agentuq.adapters.openai_agents import latest_raw_response`
- Signature: `latest_raw_response(run_result) -> Any`
- Purpose: extract the latest raw Responses object from an OpenAI Agents SDK run result
- Required / expected input shape: run result object exposing `raw_responses`
- Returns / output: the last raw Responses payload
- Caveat: raises `ValueError` if `raw_responses` is unavailable

## `probe_openrouter_model` (`Preview`)

- Import: `from agentuq.adapters import probe_openrouter_model`
- Signature: `probe_openrouter_model(model: str, supported_parameters: list[str] | None = None) -> dict[str, Any]`
- Purpose: build a declared-capability hint for OpenRouter model routing
- Key parameters: `model`, optional `supported_parameters`
- Returns / output: plain dictionary describing declared parameter support
- Caveat: this is a caller-supplied capability hint, not proof that the routed backend will actually return token details

## `probe_litellm_capability` (`Preview`)

- Import: `from agentuq.adapters import probe_litellm_capability`
- Signature: `probe_litellm_capability(model: str, provider: str | None = None, supported_openai_params: list[str] | None = None) -> dict[str, Any]`
- Purpose: build a declared-capability hint for LiteLLM routing
- Key parameters: `model`, optional `provider`, optional `supported_openai_params`
- Returns / output: plain dictionary describing declared support
- Caveat: this helper reflects caller-provided support metadata; the actual returned payload still determines runtime capability
