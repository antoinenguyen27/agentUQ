# AgentUQ

Single-pass runtime reliability instrumentation for LLM agents using token logprobs.

AgentUQ does not claim to know whether an output is true. It turns token logprobs into localized runtime signals that can change agent behavior: retry, regenerate a risky span, dry-run verify an action, block execution, or ask for user confirmation.

## What it is for

- Strictly greedy agent steps for canonical scoring, or any structured/action-bearing step in realized mode
- Structured outputs, tool calls, browser actions, SQL, code, and DSLs
- Teams that already have validators, retries, and human-in-the-loop paths

## What it is not

- A universal trust score
- A correctness oracle
- A replacement for retrieval, verification, or human review

## Canonical vs realized

- Canonical mode uses `G-NLL` and is only valid when the run is explicitly known to be greedy: `temperature=0`, `top_p=1`, and deterministic metadata.
- Realized mode uses realized-path NLL plus local token diagnostics on the actual emitted path.
- AgentUQ does not fake `G-NLL` for sampled trajectories.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

## Testing

AgentUQ uses a three-tier test strategy:

- `tests/unit`: offline deterministic tests and the required default quality gate
- `tests/contracts`: offline contract tests using sanitized captured payload fixtures
- `tests/live`: optional maintainer/contributor smoke tests against real providers/frameworks

Default pytest runs only offline tests:

```bash
python -m pytest
```

Live tests are manual, opt-in, and never required for normal OSS contribution flows:

```bash
AGENTUQ_RUN_LIVE=1 python -m pytest -m live
```

Live tests require local API keys and only assert structural invariants such as successful capture, capability detection, and `capture -> analyze -> decide` behavior. They do not assert exact model text or exact score values.

## Quick start

```python
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

adapter = OpenAIChatAdapter()
analyzer = Analyzer(UQConfig(mode="auto", policy="balanced", tolerance="balanced"))

record = adapter.capture(response, {
    "model": "gpt-4o-mini",
    "temperature": 0.0,
    "top_p": 1.0,
    "logprobs": True,
    "top_logprobs": 5,
    "deterministic": True,
})
result = analyzer.analyze_step(record, adapter.capability_report(response, {"logprobs": True, "top_logprobs": 5}))
decision = result.decision
print(result.pretty())
```

## Core objects

- `GenerationRecord`: provider-normalized generation payload
- `CapabilityReport`: what logprob structure actually came back
- `Analyzer`: shared scoring, segmentation, eventing, and degradation logic
- `Decision`: policy output with segment-level actions
- `UQResult.pretty()`: human-readable multiline rendering for CLI/log usage

## Pretty output

Use `UQResult.pretty()` when you want a readable multiline summary for a terminal, log, or trace note:

```python
print(result.pretty())
```

Available verbosity levels:

- `compact`: summary only, plus short highlights when the result is risky or degraded
- `summary`: default. Summary plus interesting segments and triggered event explanations
- `debug`: full summary, all segments, more metrics, and optional threshold tables

Plain-text output is the canonical rendering contract. It is optimized for terminals, logs, and trace notes even when Rich is not installed.

Available threshold display modes:

- `none`: never show threshold comparisons
- `triggered`: default. Show measured value vs threshold only for triggered events
- `all`: in `debug`, also print the full resolved threshold set for each segment priority

Examples:

```python
print(result.pretty())
print(result.pretty(verbosity="compact"))
print(result.pretty(verbosity="debug", show_thresholds="all"))
```

Optional Rich rendering is available if you install the extra:

```bash
pip install 'agentuq[rich]'
```

```python
result.rich_console_render()
```

Default `summary` output includes:

- analysis mode and mode reason
- aggregate primary score and score type
- overall action and rationale
- top-risk segment and risk basis
- capability summary and warnings
- interesting segments only
- triggered events with explanatory threshold comparisons when available

## How to read results

- `aggregate_primary_score` is length-dependent and summarizes the full emitted path.
- `top_risk` and `risk_basis` tell you which segment actually drove the operational recommendation.
- Treat prose-only warnings as annotation signals unless they outrank or coincide with action-bearing spans.

## Configuration model

- `policy`: action behavior after events are emitted
- `tolerance`: event sensitivity preset (`strict`, `balanced`, `lenient`)
- `thresholds`: optional numeric overrides on top of the selected tolerance preset
- `custom_rules`: optional action overrides for specific segment and event combinations

Example:

```python
config = UQConfig(
    policy="conservative",
    tolerance="strict",
    thresholds={"entropy": {"critical_action": 0.9}},
)
```

## Capability tiers

- `full`: selected-token logprobs plus top-k logprobs
- `selected_only`: selected-token logprobs only
- `none`: no usable token logprobs

Default behavior is fail-loud on missing selected-token logprobs. Top-k gaps degrade with explicit `MISSING_TOPK` events unless you require top-k.

## Included integrations

- OpenAI Responses
- OpenAI Chat Completions
- OpenAI wrapper
- LiteLLM
- OpenRouter
- LangChain wrapper/middleware
- LangGraph hooks
- Gemini
- Fireworks
- Together
- OpenAI Agents SDK helpers

## Docs

- [OpenAI quickstart](docs/quickstarts/openai.md)
- [OpenRouter quickstart](docs/quickstarts/openrouter.md)
- [LiteLLM quickstart](docs/quickstarts/litellm.md)
- [Gemini quickstart](docs/quickstarts/gemini.md)
- [Fireworks quickstart](docs/quickstarts/fireworks.md)
- [Together quickstart](docs/quickstarts/together.md)
- [LangChain quickstart](docs/quickstarts/langchain.md)
- [LangGraph quickstart](docs/quickstarts/langgraph.md)
- [OpenAI Agents quickstart](docs/quickstarts/openai_agents.md)
- [Capability tiers](docs/concepts/capability_tiers.md)
- [Canonical vs realized](docs/concepts/canonical_vs_realized.md)
- [Segmentation](docs/concepts/segmentation.md)
- [Policies](docs/concepts/policies.md)
- [Tolerance](docs/concepts/tolerance.md)
- [Testing](docs/concepts/testing.md)
- [Troubleshooting](docs/concepts/troubleshooting.md)
