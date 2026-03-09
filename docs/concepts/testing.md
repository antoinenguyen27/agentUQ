# Testing

AgentUQ uses three complementary test layers.

## `tests/unit`

Offline, deterministic tests for:

- scoring and mode selection
- segmentation
- events and policy behavior
- adapter normalization helpers
- wrapper and integration plumbing with synthetic payloads

When unit tests cover tool gating or tool-argument policy, they should use explicitly grounded synthetic spans rather than assuming provider prose implies tool-call token coverage.

This is the required default suite for contributors and maintainers.

Run it with:

```bash
python -m pytest
```

## `tests/contracts`

Offline contract tests using sanitized captured payload fixtures.

Purpose:

- catch response-shape drift
- verify adapter normalization and capability detection
- cover degraded and missing-logprob payload cases

Fixtures are checked into the repo only after removing sensitive data. Preserve only the fields needed for:

- token logprob extraction
- structured blocks and segmentation boundaries
- capability detection
- wrapper/framework metadata surfaces

Contract fixtures should model only documented provider/framework surfaces. For OpenAI-compatible tool calling, this means structural `tool_calls` plus text logprobs where available, not synthetic tool-call-token logprobs.

## `tests/live`

Optional manual smoke tests for real providers/frameworks.

Purpose:

- detect API drift
- verify that example integration paths still work with real SDKs/services

These tests are intentionally minimal and structural. They assert:

- the request succeeds
- logprobs are actually returned
- the adapter produces a `GenerationRecord`
- the analyzer produces a `UQResult`
- wrapper/framework paths attach or return UQ metadata

They do **not** assert:

- exact output text
- exact token sequence
- exact score values

## Running live tests

Live tests are skipped by default. To enable them:

```bash
AGENTUQ_RUN_LIVE=1 python -m pytest -m live
```

Required environment variables depend on which live tests you want to run:

- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `GEMINI_API_KEY`
- `FIREWORKS_API_KEY`
- `TOGETHER_API_KEY`

Optional model overrides:

- `AGENTUQ_OPENAI_RESPONSES_MODEL`
- `AGENTUQ_OPENAI_CHAT_MODEL`
- `AGENTUQ_OPENROUTER_MODEL`
- `AGENTUQ_LITELLM_MODEL`
- `AGENTUQ_GEMINI_MODEL`
- `AGENTUQ_FIREWORKS_MODEL`
- `AGENTUQ_TOGETHER_MODEL`
- `AGENTUQ_LANGCHAIN_MODEL`
- `AGENTUQ_LANGGRAPH_MODEL`
- `AGENTUQ_OPENAI_AGENTS_MODEL`

## OSS policy

For this public repo:

- live tests are maintainer/contributor local tools
- they are not part of required PR CI
- they should not rely on repo-tracked secrets or `.env` files
- secret-backed CI, if ever added later, should be manual or scheduled only

## Cost and flakiness expectations

Live tests can fail for reasons unrelated to AgentUQ:

- provider outages
- routing changes
- SDK/API version changes
- quota/rate limits
- key misconfiguration

Treat them as smoke checks, not correctness proofs.
