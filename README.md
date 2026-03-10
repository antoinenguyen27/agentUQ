# AgentUQ

Single-pass runtime reliability gate for LLM agents using token logprobs.

AgentUQ turns provider-native token logprobs into localized runtime decisions for agent steps. It does not claim to know whether an output is true. It tells you where a generation looked brittle or ambiguous and whether the workflow should continue, annotate the trace, regenerate a risky span, retry the step, dry-run verify, ask for confirmation, or block execution.

It sits above having no gate or guardrails at all, and below slower, more expensive layers such as retrieval-backed verification, sandbox execution, LLM-as-a-judge, or human review. The goal is to give agent developers a cheap first-pass reliability layer that is honest about what logprobs can and cannot say, and light enough to run on every step.

## Why teams use it

- Catch brittle action-bearing spans before execution: SQL clauses, tool arguments, selectors, URLs, paths, shell flags, and JSON leaves
- Localize risk to the exact span that matters instead of treating the whole response as one opaque score
- Spend expensive verification selectively by using AgentUQ as the first-pass gate

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Examples below assume the public package and import namespace `agentuq`.

## 30-second quickstart

Use the OpenAI Responses API for new agentic integrations.

```python
from openai import OpenAI

from agentuq import Action, Analyzer, UQConfig
from agentuq.adapters.openai_responses import OpenAIResponsesAdapter

client = OpenAI()
request_meta = {
    "model": "gpt-4.1-mini",
    "include": ["message.output_text.logprobs"],
    "top_logprobs": 5,
    "temperature": 0.0,
    "top_p": 1.0,
}
response = client.responses.create(
    model=request_meta["model"],
    input="Return a SQL query for active users created in the last 7 days.",
    include=request_meta["include"],
    top_logprobs=request_meta["top_logprobs"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
decision = result.decision

print(result.pretty())

if decision.action == Action.DRY_RUN_VERIFY:
    run_explain_before_execution(result)
elif decision.action in {Action.ASK_USER_CONFIRMATION, Action.BLOCK_EXECUTION}:
    stop_before_side_effect(result)
else:
    continue_workflow(response)
```

That is the core loop: capture the response, analyze it, then route the workflow based on `result.decision.action`.

## What decisions it can trigger

- `continue`: proceed normally
- `continue_with_annotation`: proceed, but attach the result to logs, traces, or monitoring
- `regenerate_segment`: repair only the risky leaf or clause when your framework supports structured retry
- `retry_step` / `retry_step_with_constraints`: rerun the model step with tighter instructions or narrower decoding
- `dry_run_verify`: run a safe validator before execution
- `ask_user_confirmation` / `block_execution`: stop before a side effect

See [Acting on decisions](docs/concepts/acting_on_decisions.md) for concrete integration patterns.

## What it is for

- Strictly greedy agent steps for canonical scoring, or any structured/action-bearing step in realized mode
- Structured outputs, tool calls, browser actions, SQL, code, and DSLs
- Teams that already have validators, retries, and human-in-the-loop paths

## What it is not

- A universal trust score
- A correctness oracle
- A replacement for retrieval, verification, or human review

## Why this is still valuable when models can be confidently wrong

Confident hallucinations are real. AgentUQ is valuable because it is a runtime gate, not because it is a truth oracle.

- It is good at detecting brittle local generation, ambiguous action-bearing spans, and low-confidence stretches that are worth annotating, regenerating, or verifying.
- It is especially useful on structured outputs, tool arguments, SQL, browser actions, shell commands, and other executed text where local token uncertainty is operationally meaningful.
- It does not replace retrieval, semantic verification, sandboxing, or human review for high-probability factual errors or internally consistent confabulations.

That is the right mental model: AgentUQ is the cheap first-pass gate that decides when a slower verifier should be invoked.

## Canonical vs realized

- Canonical mode uses `G-NLL` and is only valid when the step is known to be strictly greedy. In practice, `temperature=0` and `top_p=1` must be visible at analysis time.
- Realized mode uses realized-path NLL plus local token diagnostics on the actual emitted path.
- AgentUQ does not fake `G-NLL` for sampled or unknown decoding paths.

## Why this works

AgentUQ starts from the strongest black-box confidence signal an autoregressive model exposes for free: token logprobs.

- In canonical mode, AgentUQ uses greedy-path likelihood (`G-NLL`) for steps that are explicitly known to be greedy.
- In realized mode, AgentUQ uses realized-path NLL on the actual emitted tokens instead of pretending a sampled path was greedy.
- Segmentation does not invent a new score. It localizes the same sequence-likelihood signal onto action-bearing spans such as SQL, tool arguments, selectors, URLs, paths, and shell flags.
- Events and policy turn those localized signals into runtime actions.

At the sequence level, AgentUQ is operating on the standard autoregressive quantity:

```text
NLL(y | x) = Σ_t -log p(y_t | x, y_<t)
```

For non-overlapping leaf segments, AgentUQ simply decomposes that same quantity over spans so the leaf scores sum back to the whole emitted response.

## Where it sits in the reliability stack

- No gate: fastest, cheapest, least safe
- AgentUQ: single-pass, provider-native, localized, cheap enough to run on every step
- Judge / verifier / retrieval / sandbox / human review: slower and more expensive, used selectively when AgentUQ says the extra check is worth paying for

This is the intended operating model: let AgentUQ cheaply catch brittle or ambiguous steps, and reserve expensive verification for the steps that look risky.

## Research grounding

AgentUQ's method choice is intentionally narrow and research-backed:

- Greedy-path likelihood is a credible flagship object for strictly greedy runs, and recent work argues that it deserves more attention in LLM UQ: [Aichberger et al. 2026](https://arxiv.org/abs/2412.15176v2)
- Token probabilities are a meaningful internal confidence signal, though not a perfect correctness estimator: [Kumar et al. 2024](https://aclanthology.org/2024.acl-long.20/)
- Sequence likelihood is a strong black-box baseline, but raw sequence scoring alone is too blunt and wording-sensitive: [Lin et al. 2024](https://aclanthology.org/2024.emnlp-main.578/)
- Local token uncertainty remains useful for selective generation and truthfulness-oriented ranking: [Vazhentsev et al. 2025](https://aclanthology.org/2025.naacl-long.113/)
- Stronger meaning-level hallucination methods such as semantic entropy exist, but they usually need multiple generations and a higher runtime budget: [Farquhar et al. 2024](https://www.nature.com/articles/s41586-024-07421-0)

AgentUQ's product claim is therefore modest but strong: use the best lightweight probability signal the model already exposes, use it honestly, localize it to the spans that matter, and trigger cheap control actions before reaching for heavier verification.

## Common questions

<details>
<summary>Open the FAQ</summary>

**Isn't this just perplexity?**

It uses the same likelihood family, but it is doing a different job. Perplexity is usually used as a whole-sequence quality summary; AgentUQ takes mode-correct likelihood, adds local token diagnostics, and then routes that signal onto the exact spans that matter so you can decide whether to continue, retry, verify, confirm, or block. See [Canonical vs realized](docs/concepts/canonical_vs_realized.md), [Segmentation](docs/concepts/segmentation.md), and [Acting on decisions](docs/concepts/acting_on_decisions.md).

**Why should logprobs mean anything?**

They are the model's own conditional preference signal over the tokens it emitted. That makes them useful runtime telemetry: not a proof of truth, but a direct signal of where the model looked brittle, ambiguous, or unstable while generating the step. See [Research grounding](docs/concepts/research_grounding.md).

**If models can hallucinate confidently, why is this still useful?**

Because AgentUQ is a gate, not a verifier. It is valuable when you want a cheap first-pass signal for brittle or ambiguous steps, especially on structured outputs and action-bearing text, before paying for a slower layer like retrieval-backed verification, an external validator, an LLM judge, sandbox execution, or human review. See [Research grounding](docs/concepts/research_grounding.md).

**Why do you insist on greedy mode for G-NLL?**

Because `G-NLL` is meant to describe the greedy path. If the run was sampled, or the greedy settings are unknown at analysis time, then the honest thing to score is the path that actually came out. That is why AgentUQ switches to realized mode instead of pretending a sampled path was canonical. See [Canonical vs realized](docs/concepts/canonical_vs_realized.md).

**Does segmentation break the math?**

No. Segmentation does not invent a new uncertainty score for SQL, selectors, or prose. For non-overlapping leaf spans, it simply attributes the same emitted-path likelihood to smaller operational units, which is what makes the score useful inside agent loops. See [Segmentation](docs/concepts/segmentation.md) and [Research grounding](docs/concepts/research_grounding.md).

**Are segment scores independent?**

No. A later segment is still conditioned on the prompt and everything the model already emitted before it. Segment scores are local diagnostics within one generated path, not separate independent probabilities that should be multiplied together. See [Research grounding](docs/concepts/research_grounding.md).

**Why not use semantic entropy or another stronger hallucination method?**

Those methods can be stronger in some settings, but they usually require multiple generations or extra semantic comparison steps. AgentUQ is optimized for a different operating point: single-pass, black-box, low-latency runtime gating that is cheap enough to run on every step. See [Research grounding](docs/concepts/research_grounding.md).

**What is AgentUQ actually good at?**

It is strongest on structured outputs and action-bearing spans where local uncertainty is operationally meaningful: tool arguments, JSON leaves, SQL, browser actions, selectors, URLs, shell commands, and other text that may be executed or validated. That is where a localized risk signal is most useful. See [Segmentation](docs/concepts/segmentation.md) and [Acting on decisions](docs/concepts/acting_on_decisions.md).

**What should I do with the result?**

Use it to route the next step. On low risk, continue. When only prose looks uncertain, continue and annotate the trace. When one field or clause is risky, repair or regenerate that part if your framework supports it. When the whole step is unstable, reprompt the agent or retry with tighter constraints. When the answer needs more external grounding, retrieve more context or hand off to a stronger verifier. Before side effects, dry-run, ask for confirmation, or block. See [Acting on decisions](docs/concepts/acting_on_decisions.md).

**How should I tune the system?**

Start with `policy` and `tolerance`, not raw thresholds. `policy` controls what AgentUQ does after it sees risk, such as whether it prefers annotation, retry, confirmation, or blocking. `tolerance` controls how easily it decides something looks risky in the first place. Only after those feel roughly right should you use `thresholds` for numeric fine-tuning, and `custom_rules` when the defaults are mostly correct but one segment/event case needs a specific override. See [Policies](docs/concepts/policies.md), [Tolerance](docs/concepts/tolerance.md), and [Acting on decisions](docs/concepts/acting_on_decisions.md).

</details>

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

## Core objects

- `GenerationRecord`: provider-normalized generation payload
- `CapabilityReport`: what logprob structure actually came back
- `Analyzer`: shared scoring, segmentation, eventing, and degradation logic
- `Decision`: policy output with segment-level actions
- `UQResult.pretty()`: human-readable multiline rendering for CLI/log usage

## Close the loop

AgentUQ is meant to drive runtime behavior, not just terminal output.

The public loop is:

1. capture the model response into a `GenerationRecord`
2. analyze it with `Analyzer`
3. read `result.decision.action`
4. branch into your retry, verification, confirmation, or blocking path

Use `result.decision.segment_actions` when you need the per-segment action map, and use the segment list when you need to inspect which exact span triggered the recommendation.

As a practical default:

- `continue`: proceed normally
- `continue_with_annotation`: proceed, but log or attach the result to traces
- `regenerate_segment`: rerun only the risky field or clause if your framework supports structured retry
- `retry_step` / `retry_step_with_constraints`: rerun the model step, usually with tighter instructions or lower temperature
- `dry_run_verify`: run a safe validator before executing the action
- `ask_user_confirmation`: pause the workflow and surface the risky span to the user
- `block_execution`: fail closed before any side effect

Advanced actions such as `escalate_to_human`, `emit_webhook`, and `custom` are available in the action model, but are typically used through `custom_rules` and user-defined dispatch code rather than the default presets.

See [Acting on decisions](docs/concepts/acting_on_decisions.md) for concrete loop patterns and integration examples.

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
- whole-response score and score type
- overall action and rationale
- decision-driving segment and its basis
- capability summary and warnings
- interesting segments only
- triggered events with explanatory threshold comparisons when available

## How to read results

- `whole_response_score` is length-dependent and summarizes the full emitted path.
- `decision_driving_segment` and `decision_driving_segments` tell you which segment actually drove the operational recommendation.
- Treat prose-only warnings as annotation signals unless they outrank or coincide with action-bearing spans.
- Heuristic action-bearing spans come from explicit literal contexts such as structured blocks, fenced or inline code, exact ReAct labels, standalone snippet lines, and short snippet-intro tails like `Query: ...`.
- When a final answer contains embedded literal spans such as SQL or browser DSL, AgentUQ emits residual prose slices around those spans rather than one wrapper segment for the whole answer.
- Short inline literals that are explicit but not recognized as action-bearing stay inside the surrounding prose segment instead of becoming standalone text slices.

See [Reading results](docs/concepts/reading_results.md) for a fuller guide to metrics, events, thresholds, and what comparisons are actually meaningful.

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

Reach for the knobs in this order:

- `policy` when you want a different default action behavior
- `tolerance` when you want events to fire earlier or later
- `thresholds` when you need numeric fine-tuning of one metric or priority class
- `custom_rules` when the defaults are mostly right but a specific segment/event combination needs a different action

For the exact public surfaces, signatures, and fields, see the [API Reference](docs/concepts/public_api.md). For symptom-based tuning, see [Tolerance](docs/concepts/tolerance.md).

## Capability tiers

- `full`: selected-token logprobs plus top-k logprobs
- `selected_only`: selected-token logprobs only
- `none`: no usable token logprobs

Default behavior is fail-loud on missing selected-token logprobs. Top-k gaps degrade with explicit `MISSING_TOPK` events unless you require top-k.

## Included integrations

- OpenAI Responses
- OpenAI Chat Completions
- OpenAI Agents SDK helpers
- LiteLLM
- OpenRouter
- LangChain wrapper/middleware
- LangGraph hooks
- Gemini
- Fireworks
- Together

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
- [API Reference](docs/concepts/public_api.md)
- [Provider and framework capabilities](docs/concepts/provider_capabilities.md)
- [Reading results](docs/concepts/reading_results.md)
- [Segmentation](docs/concepts/segmentation.md)
- [Research grounding](docs/concepts/research_grounding.md)
- [Acting on decisions](docs/concepts/acting_on_decisions.md)
- [Policies](docs/concepts/policies.md)
- [Tolerance](docs/concepts/tolerance.md)
- [Testing](docs/concepts/testing.md)
- [Troubleshooting](docs/concepts/troubleshooting.md)
