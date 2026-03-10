---
title: Utilities and Errors
description: Advanced helper utilities and public error types for fail-loud or integration-heavy deployments.
slug: /reference/utilities-and-errors
sidebar_position: 15
---

# Utilities and Errors

## `request_params` (`Advanced`)

- Import: `from agentuq.request_params import request_params`
- Signature: `request_params(provider: str, mode: str = "auto", topk: int = 5, transport: str | None = None) -> dict`
- Purpose: convenience helper for provider-specific request parameter defaults
- Key parameters: `provider` in `openai | openrouter | litellm | gemini | fireworks | together`, optional OpenAI `transport` in `responses | chat`, `mode` in `auto | canonical | realized`, `topk`
- Returns / output: provider-specific request metadata dictionary
- Caveat: this helper sets request intent, not actual provider capability; unsupported providers or invalid OpenAI transport values raise `ValueError`

## Error base class (`Advanced`)

- Import: `from agentuq.schemas.errors import AgentUQError`
- Purpose: base exception carrying actionable metadata
- Structured fields: `message`, `provider`, `transport`, `model`, `requested_params`, `observed_capability`, `remediation`
- Output behavior: stringifies into a joined, operator-readable error message

## Public error types (`Advanced`)

All public error types inherit from `AgentUQError` and live in `agentuq.schemas.errors`.

| Error | When it is used |
| --- | --- |
| `LogprobsNotRequestedError` | Logprobs were required but not requested. |
| `SelectedTokenLogprobsUnavailableError` | Selected-token logprobs were requested but not returned. |
| `TopKLogprobsUnavailableError` | Top-k logprobs were required but unavailable. |
| `ProviderDroppedRequestedParameterError` | Requested logprob parameters appear to have been dropped by the provider or route. |
| `ModelCapabilityUnknownProbeRequired` | Capability probing is required before making a stronger assumption. |
| `UnsupportedForCanonicalModeError` | Canonical mode was requested but strict greedy conditions were not established. |
| `CapabilityProbeFailedError` | Capability probe flow failed. |

- Caveat: these types are most useful in fail-loud or integration-heavy deployments; see [Troubleshooting](../concepts/troubleshooting.md)

