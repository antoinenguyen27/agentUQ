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

## Quick start

```python
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

adapter = OpenAIChatAdapter()
analyzer = Analyzer(UQConfig(mode="auto", policy="balanced"))

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
```

## Core objects

- `GenerationRecord`: provider-normalized generation payload
- `CapabilityReport`: what logprob structure actually came back
- `Analyzer`: shared scoring, segmentation, eventing, and degradation logic
- `Decision`: policy output with segment-level actions

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
- [Troubleshooting](docs/concepts/troubleshooting.md)
