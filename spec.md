# Logprob Runtime Reliability Layer for LLM Agents — Product & Technical Specification
**ProjectName**: AgentUQ
**Status:** implementation-ready v1
**Target:** Python-first OSS library, with a TypeScript port later
**Scope:** single-pass, black-box, logprob-native runtime reliability instrumentation for LLM agents
**Primary deployment environments:** OpenAI Responses API / Chat Completions, LangGraph / LangChain, provider adapters for any API returning token logprobs

---

## 1. Executive summary

This product is **not** a magical “trust score for AI.” It is a **runtime control layer** that turns token logprobs into operational signals agent developers can actually use.

The product’s job is to answer:

* should this agent step continue,
* should only a risky span be regenerated,
* should a tool call be blocked or dry-run verified,
* should the user be asked for confirmation,
* or should the run be escalated to a human.

The library is built around a hard product truth:

* **uncertainty is useful when it changes behavior**, not when it only produces a number.

Accordingly, the library exposes:

1. **primary uncertainty scores** grounded in current probability-based UQ literature,
2. **segment-level diagnostics** that localize risk inside action-bearing outputs,
3. **event detectors** that convert metrics into interpretable failure signals,
4. **policy hooks** that integrate directly into agent loops.

The flagship academic method is **G-NLL** under strictly greedy decoding conditions. When those conditions are not met, the library falls back to **realized-path probability diagnostics** rather than pretending G-NLL still applies.

---

## 2. Honest framing: where this is genuinely useful, and where it is not

### 2.1 What this product is genuinely useful for

This library is useful when:

* the developer already runs an agent through structured steps and wants **runtime gating**,
* the provider returns **selected-token logprobs** and preferably **top-k logprobs**,
* the developer wants a **cheap, single-pass signal** rather than expensive sampling or verifier models,
* the workflow contains **action-bearing spans** whose local uncertainty matters more than a global answer score,
* the system already has retry / confirm / verify control points where a reliability signal can trigger action.

Most useful current scenarios:

* tool selection and tool argument generation,
* structured JSON outputs,
* browser / UI actions,
* SQL / code / DSL emission,
* retrieval-backed final answers under low temperature,
* enterprise agents where deterministic behavior is preferred.

### 2.2 What this product does **not** do

This library does **not**:

* prove correctness,
* detect all hallucinations,
* replace retrieval, external verification, or task-specific validators,
* make long-horizon agent reasoning “safe” by itself,
* make scores directly comparable across every model, temperature, prompt style, and task.

### 2.3 Why this is still worth building

The current practical value is not “universal truth estimation.” It is:

* **cheap ranking of risky steps**,
* **early warning for brittle actions**,
* **localized regeneration of the part most likely to fail**,
* **instrumentation for agent developers and framework builders**,
* **a cheap first-pass gate that decides when slower verification is worth paying for**.

This is real product value today.

### 2.4 The core limitation to state plainly

Single-pass logprob UQ is strongest when:

* the model actually runs greedily when canonical scoring is desired,
* outputs are structured or action-bearing,
* developers care about ranking and gating, not perfect calibration.

It is materially weaker when:

* outputs are long and stylistically variable,
* temperature is meaningfully non-zero,
* errors are subtle semantic / world-model / planning failures that remain locally high-probability,
* the product is expected to act like a complete correctness oracle.

The product must say this plainly in the README.

Confident hallucinations do not invalidate the product. They define its boundary. The library is a runtime gate for brittle or ambiguous steps, not a proof system for semantic correctness.

### 2.5 Where this sits in the reliability stack

The intended deployment position is:

* above having **no runtime gate** at all,
* below **LLM-as-a-judge**, retrieval-backed verification, sandbox execution, or human review,
* and cheap enough to run on **every model step** in an agent loop.

The design goal is selective escalation:

* use AgentUQ as the default low-latency gate,
* trigger retries, annotations, dry-runs, or confirmations when the local signal is concerning,
* escalate to slower and more expensive verification only when the step looks risky enough to justify the cost.

---

## 3. Product thesis

**Product thesis:** existing agent frameworks are missing a reusable, provider-friendly **runtime reliability instrumentation layer**.

Most current agent stacks already have:

* orchestrators,
* tool calling,
* state,
* retries,
* human-in-the-loop,
* tracing.

What they usually lack is a rigorous, reusable answer to:

* “how risky is this step,”
* “which exact span is risky,”
* “what action should I take because of that risk.”

This library fills that gap.

---

## 4. Product requirements

### 4.1 Must-have requirements

* **single-pass only** at runtime
* **black-box**: no hidden states, no fine-tuning, no auxiliary teacher model at inference
* **works with provider APIs exposing logprobs**
* **no deep-learning calibration requirement**
* **first-class support for agent frameworks**, not just notebooks
* **risk localization** to segments, fields, and spans
* **event-driven policies**, not score-only APIs
* **graceful degradation** when only selected-token logprobs are available and top-k is absent

### 4.2 Non-goals for v1

* multi-sample semantic methods
* trainable calibrators
* white-box probe methods
* claim extraction + NLI pipelines
* model-specific fine-tuning

---

## 5. Method selection and product decisions

### 5.1 Method families considered

#### A. G-NLL / maximum-sequence-probability family

Pros:

* strong theoretical grounding,
* single sequence,
* deterministic,
* cheap,
* academically credible.

Cons:

* assumes approximation of the **most likely output sequence**,
* aligned to strict greedy use,
* not faithful for genuinely sampled trajectories,
* raw sums are length-sensitive.

Decision:

* **primary flagship method** for strictly greedy runs.
* aligned with the recent argument in [Aichberger et al. 2026](https://arxiv.org/abs/2412.15176v2) that greedy-path NLL deserves renewed attention in LLM uncertainty estimation.

#### B. Raw realized-path NLL / mean logprob / perplexity family

Pros:

* trivial to compute,
* aligned with the actual emitted tokens,
* works even when the path is sampled.

Cons:

* confounds uncertainty with decoding stochasticity,
* weaker theoretical story than G-NLL,
* raw averages often flatten the interesting low-probability events.

Decision:

* **fallback scoring family when G-NLL conditions are not met**.

#### C. Token entropy / margin / rank diagnostics

Pros:

* local and interpretable,
* useful for span detection,
* excellent for policy events.

Cons:

* require top-k logprobs for best effect,
* token-level confidence becomes less reliable on long-form, instruction-tuned outputs.

Decision:

* **mandatory companion diagnostics** for policy and localization,
* not the flagship scalar.

#### D. MARS / SAR / relevance-weighted scoring

Pros:

* address token-importance inequality,
* often improve QA-style uncertainty ranking.

Cons:

* extra models / extra complexity,
* less clean black-box portability,
* evidence base is more QA-centric than agent-centric,
* worse fit for a 24-hour production-worthy OSS v1.

Decision:

* **not in v1 core**,
* may be added later as optional scoring plugins.

#### E. CCP / claim-conditioned and fact-checking style methods

Pros:

* strong for claim-level factuality.

Cons:

* specialized to claim decomposition and factuality,
* not general runtime agent UQ,
* typically needs extra NLP components.

Decision:

* **explicitly out of scope for v1**.

#### F. HALT-style learned time-series methods

Pros:

* preserve trajectory structure,
* promising on long outputs.

Cons:

* require training data,
* model-specific generalization concerns,
* outside the “just works without calibration” constraint.

Decision:

* **not in v1**.

### 5.2 Final method policy

The runtime engine uses **mode-aware method selection**:

1. **Canonical mode** → use **G-NLL**
2. **Realized mode** → use **realized-path NLL + token diagnostics**
3. **Diagnostics mode** → expose entropy / margin / rank events regardless of primary mode when top-k is available

This is the central product choice.

---

## 6. When to use which method

### 6.1 Canonical mode (G-NLL)

Use G-NLL only when all of the following are true:

* generation is known to be greedy,
* temperature is exactly 0,
* top-p is exactly 1,
* there is no meaningful stochastic exploration objective,
* the score is intended to represent **confidence in the model’s canonical answer / action**,
* the output is a whole deterministic segment rather than a sampled creative continuation.

Recommended default condition:

* `temperature == 0` **and** `top_p == 1` **and** framework marks the step as `deterministic=True`

If any of these are unknown, default to **realized mode**.

### 6.2 Realized mode

Use realized-path scoring when:

* temperature is meaningfully non-zero,
* the actual emitted tokens are what matters operationally,
* the step contains tool arguments, structured fields, code, SQL, browser commands, or any executed text,
* the provider returns logprobs for the sampled sequence but the developer cannot or should not recompute a greedy pass.

### 6.3 Important rule

For **structured action-bearing segments**, even when the overall run is deterministic, the product still exposes realized-path local diagnostics because the actual emitted field values are what developers must verify and potentially regenerate.

---

## 7. Mathematical specification

### 7.1 Notation

For a segment with tokens `y_1 ... y_T`, let:

* `l_t = log p(y_t | x, y_{<t})` be the logprob of the selected token,
* `p_t = exp(l_t)`,
* `topk_t = {(v_j, l_{t,j})}` be the available top-k alternatives,
* `K_t = |topk_t|`.

Define token surprise:

* `s_t = -l_t`

### 7.2 G-NLL

The ideal quantity is the negative log-likelihood of the most likely sequence:

* `NLL(y*) = - log p(y* | x)` where `y* = argmax_y p(y | x)`

Because exact search over sequences is intractable, the practical approximation is tokenwise greedy decoding. The product defines canonical G-NLL for a greedy-generated segment as:

* `G_NLL(seg) = - Σ_t log p(g_t | x, g_{<t})`
  where `g_t` is the greedily selected token at step `t`.

**Operational rule:** only compute this from a genuinely greedy generation path. Do **not** claim that the top-1 alternative under a sampled prefix equals G-NLL.

### 7.3 Realized-path NLL

For a sampled or unknown-decoding segment:

* `R_NLL(seg) = - Σ_t log p(y_t | x, y_{<t}) = Σ_t s_t`

This is the primary fallback scalar.

When non-overlapping leaf segments partition the emitted path, realized-path NLL decomposes additively across those leaves:

* `R_NLL(step) = Σ_i R_NLL(seg_i)`

This is why segmentation is mathematically honest: it localizes the same emitted-path likelihood object instead of inventing a separate score family for each span type.

### 7.4 Auxiliary normalized metrics

Because raw sums scale with length, the product also computes:

* `avg_surprise = (1/T) Σ_t s_t`
* `max_surprise = max_t s_t`
* `p95_surprise = 95th percentile of {s_t}`
* `tail_surprise_mean = mean of top 10% highest s_t`

These are **policy metrics**, not the flagship ranking metric.

### 7.5 Margin metrics

If top-k is available and contains the top two tokens:

* `margin_log_t = l_top1_t - l_top2_t`
* `margin_prob_t = exp(l_top1_t) - exp(l_top2_t)`

Use `margin_log_t` internally for numerical stability.

Segment summaries:

* `mean_margin_log`
* `min_margin_log`
* `low_margin_rate(τ) = (1/T) Σ 1[margin_log_t < τ]`
* `low_margin_run_max(τ)` = max consecutive tokens with margin below threshold.

### 7.6 Rank diagnostics

For sampled mode with top-k available:

* `rank_t = rank of emitted token among known alternatives`
* if emitted token not in returned top-k, set `rank_t > K_t` and mark `off_topk_t = 1`

Segment summaries:

* `off_top1_rate`
* `off_topk_rate`
* `off_top1_run_max`

### 7.7 Approximate entropy

When top-k is available, compute truncated, renormalized entropy:

* collect returned alternatives and the selected token if absent,
* renormalize over this partial set,
* `H_hat_t = - Σ_j p_hat_{t,j} log p_hat_{t,j}`

This is an approximation and must be labeled as such in docs.

Segment summaries:

* `mean_entropy_hat`
* `max_entropy_hat`
* `high_entropy_rate(τ)`
* `high_entropy_run_max(τ)`

### 7.8 Primary score exposure

The public API exposes:

* `primary_score`
* `primary_score_type` ∈ `{g_nll, realized_nll}`

Rule:

* canonical mode → `primary_score = G_NLL`
* realized mode → `primary_score = R_NLL`

### 7.9 Policy score

The product does **not** present a fake universally calibrated 0–1 correctness probability.

Instead, policy decisions are driven by:

* segment type,
* event triggers,
* raw / normalized metrics,
* optional preset policies.

---

## 8. Segmentation specification

### 8.1 Why segmentation is mandatory

Whole-trace scoring is too blunt for agent systems. Long sequences accumulate ordinary probability mass and hide the locally risky span that matters operationally.

Therefore, the product treats segmentation as a first-class requirement, not a convenience.

For non-overlapping leaf segments, segmentation does not change the underlying score family. It attributes the same sequence-likelihood object to the spans that matter operationally, such as SQL clauses, selectors, URLs, shell flags, and prose slices.

### 8.2 Segmentation hierarchy

The library segments at three levels.

#### Level 0 — invocation boundary

Each model invocation is one `StepRecord`.
Examples:

* planner LLM call,
* tool-argument generation call,
* post-tool interpretation call,
* final answer call.

#### Level 1 — semantic block segmentation

Within a step, split into semantic blocks using provider structure first, then explicit literal contexts:

* assistant natural language text blocks,
* function / tool name,
* tool argument string,
* structured JSON output,
* fenced code / SQL / shell block,
* inline code span,
* exact ReAct-labeled block,
* standalone snippet line or explicit snippet tail,
* final answer or observation text block.

Text blocks are structural containers. If they contain embedded action-bearing child spans, the implementation emits residual prose slices around those children rather than one scored wrapper segment for the whole block.

#### Level 2 — atomic actionable segments

Further split action-bearing blocks into minimal units that developers can regenerate or verify:

* tool name token span,
* each JSON leaf value by JSONPath,
* each SQL clause (`SELECT`, `WHERE`, `JOIN`, `LIMIT`),
* each browser command and each argument,
* each shell command and each flag/value pair,
* each URL / path / identifier span,
* each code line in small snippets or each AST leaf when parsable.

### 8.3 Provider-first segmentation rules

#### OpenAI Responses / Chat Completions

Preferred source of truth:

* separate `output_text` items,
* function call names,
* function call arguments,
* tool call outputs returned to the model,
* streamed argument deltas if available.

#### LangGraph / LangChain

Preferred source of truth:

* one model node invocation = one `StepRecord`,
* tool nodes separate from model nodes,
* attach UQ analysis after each model node and before executing any external side effect.

### 8.4 Syntax-aware sub-segmentation

If provider structure is insufficient, parse content by format.

#### ReAct-style text

Detect prefixes:

* `Thought:`
* `Action:`
* `Action Input:`
* `Observation:`
* `Final Answer:`

Score `Action` and `Action Input` more strictly than `Thought`.

#### JSON

Parse and score by JSONPath leaves.

* punctuation tokens tracked but downweighted for policy,
* leaf strings / numbers / enums become atomic segments.

#### Browser / tool DSL

Example commands:

* `click(selector="#submit")`
* `type(selector="#email", text="...")`
* `navigate(url="...")`

For v1 heuristics, detect only documented command forms in explicit literal contexts. Each command is a segment; each recognized argument value is an atomic child segment.

#### SQL

Only detect SQL in explicit literal contexts such as structured blocks, fenced blocks, inline code, standalone snippet lines, or explicit snippet tails.

Emit `sql_clause` segments for top-level clauses such as:

* `SELECT ...`
* `FROM ...`
* `WHERE ...`
* `JOIN ...`
* `GROUP BY ...`
* `ORDER BY ...`
* `LIMIT ...`

#### Code

Emit `code_statement` segments for recognizable code statements in explicit literal contexts. v1 does not expose AST-leaf, identifier, or literal sub-segmentation for code.

#### Shell

Only detect shell commands in supported command contexts such as fenced shell blocks, prompt-prefixed lines, explicit command labels, and inline code spans.

Emit:

* command head as `identifier` or `path`
* `shell_flag`
* `shell_value`
* `url`
* `path`

### 8.5 Segment kinds

The product defines these segment kinds:

* `reasoning_text`
* `final_answer_text`
* `tool_name`
* `tool_arguments_raw`
* `tool_argument_leaf`
* `json_leaf`
* `browser_action`
* `browser_selector`
* `browser_text_value`
* `sql_clause`
* `code_statement`
* `identifier`
* `url`
* `path`
* `shell_flag`
* `shell_value`
* `unknown_text`

### 8.6 Segment priority classes

Each segment kind maps to an operational priority:

* **critical_action**: `tool_name`, `browser_action`, `browser_selector`, `url`, `identifier`, `path`, `sql_clause`, `shell_flag`, `shell_value`
* **important_action**: `tool_arguments_raw`, `tool_argument_leaf`, `json_leaf`, `browser_text_value`, `code_statement`
* **informational**: final prose answer and unknown text
* **low_priority**: reasoning text

Policies are stricter for higher-priority classes.

---

## 9. Event engine

### 9.1 Design goal

Events convert raw metrics into interpretable signals developers can act on.

### 9.2 Built-in events

#### `LOW_MARGIN_CLUSTER`

Triggered when:

* `low_margin_run_max(τ_margin) >= min_run`

Interpretation:

* model repeatedly cannot clearly separate top candidates.

#### `HIGH_ENTROPY_CLUSTER`

Triggered when:

* `high_entropy_run_max(τ_entropy) >= min_run`

Interpretation:

* local distribution is diffuse; output region is unstable.

#### `LOW_PROB_SPIKE`

Triggered when:

* `max_surprise >= τ_spike`

Interpretation:

* one token or field is highly improbable.

#### `TAIL_RISK_HEAVY`

Triggered when:

* `tail_surprise_mean >= τ_tail`

Interpretation:

* segment contains multiple unusually improbable tokens rather than a single anomaly.

#### `OFF_TOP1_BURST`

Sampled mode only.
Triggered when:

* `off_top1_run_max >= min_run` or `off_top1_rate >= τ_rate`

Interpretation:

* emitted trajectory repeatedly deviates from the local argmax path.

#### `OFF_TOPK_TOKEN`

Sampled mode only.
Triggered when any emitted token is not present in returned top-k.

Interpretation:

* severe stochastic / low-confidence deviation.

#### `ACTION_HEAD_UNCERTAIN`

Triggered on `tool_name`, `browser_action`, `sql_clause`, etc. when:

* `mean_margin_log < τ_action_head` or `avg_surprise > τ_action_head_surprise`

Interpretation:

* the action choice itself is unstable.

#### `ARGUMENT_VALUE_UNCERTAIN`

Triggered on leaf values when:

* `avg_surprise >= τ_leaf` or `LOW_PROB_SPIKE` in the leaf span.

Interpretation:

* the value emitted for a parameter is brittle.

#### `SCHEMA_INVALID`

Triggered when JSON / structured output fails parsing or schema validation.

Interpretation:

* do not execute; regenerate or fail closed.

#### `TEMPERATURE_MISMATCH`

Triggered when caller requests canonical scoring but run metadata indicates sampled / unknown decoding.

Interpretation:

* downgrade to realized mode.

#### `MISSING_TOPK`

Triggered when a policy requires entropy / margin / rank events but only selected-token logprobs are available.

Interpretation:

* continue with degraded diagnostics and log capability gap.

### 9.3 Event severity

Event severities:

* `info`
* `warn`
* `high`
* `critical`

Severity depends on both event type and segment priority class.
For example:

* `LOW_PROB_SPIKE` in final prose → `warn`
* `LOW_PROB_SPIKE` in tool name → `critical`

---

## 10. Policy engine

### 10.1 Design principle

The product should not force users to invent raw thresholds from scratch.

Default interface:

* policy preset + optional per-segment overrides.

### 10.2 Built-in actions

The policy engine supports these actions:

* `continue`
* `continue_with_annotation`
* `regenerate_segment`
* `retry_step`
* `retry_step_with_constraints`
* `dry_run_verify`
* `ask_user_confirmation`
* `block_execution`
* `escalate_to_human`
* `emit_webhook`
* `custom`

### 10.3 Built-in policies

#### `balanced` (default)

* reasoning text: annotate only unless severe
* final prose: regenerate only on multiple severe events
* tool name: block or retry on any critical event
* argument leaves: regenerate segment on high or critical event
* destructive actions: ask confirmation on any high event

#### `conservative`

* more retries,
* confirmation for medium-risk external actions,
* block on schema failures or action-head instability.

#### `aggressive`

* fewer retries,
* mainly annotative except for critical action spans.

### 10.4 Built-in tolerance presets

#### `strict`

* emit events earlier,
* use lower surprise thresholds and higher low-margin sensitivity,
* suitable for high-trust or side-effectful workflows.

#### `balanced` (default)

* baseline event sensitivity,
* recommended for most integrations.

#### `lenient`

* emit fewer events,
* require stronger evidence before flagging a segment.

### 10.5 Default decision rules

#### Tool name

* if `ACTION_HEAD_UNCERTAIN` or `LOW_PROB_SPIKE` → `retry_step_with_constraints`
* if repeated after retry → `block_execution`

#### Tool argument leaf

* if `ARGUMENT_VALUE_UNCERTAIN` → `regenerate_segment`
* if schema invalid after one retry → `block_execution`

#### Browser selector / URL / identifier / path / shell flag / shell value

* if `LOW_PROB_SPIKE` or `LOW_MARGIN_CLUSTER` → `ask_user_confirmation`

#### SQL clause

* on any `high` or `critical` event → `dry_run_verify`
* if dry-run fails or uncertainty remains → `ask_user_confirmation` or `block_execution`

#### Final prose answer

* if only prose and no side effect: `continue_with_annotation` by default
* if answering in high-trust workflow: `retry_step` or hand off to verifier configured by user

### 10.6 Custom rule API

Developers can define custom rules declaratively.

Declarative YAML example:

```yaml
policies:
  - when:
      segment_kind: tool_argument_leaf
      events_any: [ARGUMENT_VALUE_UNCERTAIN, LOW_PROB_SPIKE]
    then: regenerate_segment

  - when:
      segment_priority: critical_action
      severity_at_least: high
    then: ask_user_confirmation
```

Current implementation supports declarative `custom_rules` matched in order against:

* `segment_kind`
* `segment_priority`
* `events_any`
* `severity_at_least`

The first matching rule wins and overrides the built-in preset decision for that segment.

---

## 11. Configuration model

### 11.1 Top-level config

```python
UQConfig(
    mode="auto",  # auto | canonical | realized
    policy="balanced",  # conservative | balanced | aggressive | custom
    tolerance="balanced",  # strict | balanced | lenient
    thresholds=ThresholdConfig(...),  # optional numeric overrides
    segmentation=SegmentationConfig(...),
    integrations=IntegrationConfig(...),
)
```

### 11.2 Mode selection

* `auto` (default): choose canonical vs realized mode based on metadata
* `canonical`: require deterministic conditions; otherwise raise `TEMPERATURE_MISMATCH`
* `realized`: always use realized-path mode

### 11.3 Tolerance presets

Tolerance presets define the base threshold table used for event emission.

* `strict`: earlier event emission
* `balanced`: baseline defaults
* `lenient`: later event emission

### 11.4 Threshold config

Thresholds are grouped by metric and segment priority, not one universal number. These values act as overrides on top of the selected tolerance preset.

Example:

```python
ThresholdConfig(
    low_margin_log={
        "critical_action": 0.35,
        "important_action": 0.25,
        "informational": 0.15,
    },
    entropy={
        "critical_action": 1.20,
        "important_action": 1.50,
        "informational": 1.80,
    },
    spike_surprise={
        "critical_action": 3.5,
        "important_action": 4.0,
        "informational": 5.0,
    },
    min_run=2,
)
```

Partial overrides are valid. Missing values fall back to the selected tolerance preset.

### 11.5 Why no single global threshold

Raw probability metrics vary by:

* model family,
* tokenizer,
* decoding parameters,
* segment length,
* segment type.

Therefore the product must not pretend one global scalar threshold is universally meaningful.

### 11.6 User overrides

Users may override:

* built-in tolerance presets,
* specific numeric thresholds,
* per-segment decision actions via custom rules.

This version does not expose first-class event enable / disable toggles or a separate destructive-action confirmation settings surface.

---

## 12. Integration architecture

### 12.1 Design principle: normalize once, integrate everywhere

The product must **not** be designed as a deep inheritance tree such as:

* `AgentUQ.Framework.Provider.Model.SpecialCase`

That shape is brittle, unpleasant to use, and hard to maintain as providers evolve.

Instead, the implementation must use four small, stable concepts:

1. `GenerationRecord`
2. `CapabilityReport`
3. `Analyzer`
4. `Decision`

This is the core abstraction boundary.

### 12.2 Core normalized objects

#### `GenerationRecord`

A provider/framework-agnostic representation of one model generation.

```python
GenerationRecord(
    provider: str,
    transport: str,            # direct_api | litellm | openrouter | langchain | openai_agents
    model: str,
    request_id: str | None,
    temperature: float | None,
    top_p: float | None,
    max_tokens: int | None,
    stream: bool | None,
    step_kind: str | None,
    raw_text: str | None,
    selected_tokens: list[str],
    selected_logprobs: list[float] | None,
    top_logprobs: list[list[TopToken]] | None,
    structured_blocks: list[StructuredBlock],
    metadata: dict,
)
```

#### `CapabilityReport`

Truthful report of what the runtime actually provided.

```python
CapabilityReport(
    selected_token_logprobs: bool,
    topk_logprobs: bool,
    topk_k: int | None,
    structured_blocks: bool,
    function_call_structure: bool,
    provider_declared_support: bool | None,
    request_attempted_logprobs: bool,
    request_attempted_topk: int | None,
    degraded_reason: str | None,
)
```

#### `Analyzer`

Consumes `GenerationRecord` and `CapabilityReport`, produces `UQResult`.

#### `Decision`

A framework-agnostic object containing:

* chosen policy action,
* rationale,
* segment-level actions,
* optional integration hooks.

### 12.3 Adapter design

Every integration must be implemented as a **thin adapter** that only does three jobs:

1. convert request/response objects into `GenerationRecord`,
2. construct `CapabilityReport`,
3. surface provider/framework metadata relevant to UQ.

Adapters must **not** duplicate scoring logic.
All scoring logic lives in the shared analysis engine.

### 12.4 Capability detection model

The library must determine logprob support using this order:

#### Phase 1 — Declared support

If the provider/gateway/framework exposes parameter capability metadata, inspect it first.
Examples:

* LiteLLM supported OpenAI-style params,
* OpenRouter model `supported_parameters`,
* provider SDK model capability docs if exposed programmatically.

#### Phase 2 — Requested support

Track what the caller actually requested:

* `logprobs` / `responseLogprobs`,
* `top_logprobs` / `logprobs=k`,
* strict structure / tool calling / schema mode.

#### Phase 3 — Observed support

Inspect the actual response payload.
If logprobs were requested but absent, mark the result as degraded rather than pretending they were returned.

### 12.5 Capability tiers

The engine must support exactly these capability tiers:

* `full`: selected-token logprobs + top-k logprobs
* `selected_only`: selected-token logprobs only
* `none`: no usable token logprobs

Behavior:

* `full` → full diagnostics and event engine
* `selected_only` → G-NLL for strictly greedy runs or realized-NLL otherwise, plus surprise-only events and no entropy or rank events
* `none` → explicit unsupported or degraded result, depending on config

### 12.6 Failure and degradation policy

Default behavior for missing capabilities must be **fail-loud**, not silent.

Config flags:

```python
CapabilityConfig(
    require_logprobs=True,
    require_topk=False,
    fail_on_missing_logprobs=True,
    fail_on_missing_topk=False,
    allow_degraded_mode=True,
)
```

Default semantics:

* if logprobs were required and not returned → raise descriptive error
* if top-k was preferred but not returned → continue in degraded mode and emit `MISSING_TOPK`
* if canonical mode was requested but decoding metadata indicates non-greedy or unknown decoding → raise or downgrade based on config

### 12.7 Error model

Required public errors:

* `LogprobsNotRequestedError`
* `SelectedTokenLogprobsUnavailableError`
* `TopKLogprobsUnavailableError`
* `ProviderDroppedRequestedParameterError`
* `ModelCapabilityUnknownProbeRequired`
* `UnsupportedForCanonicalModeError`
* `CapabilityProbeFailedError`

These errors must include:

* provider / transport / model,
* requested params,
* observed capability,
* remediation steps.

### 12.8 Non-streaming support requirement

The spec explicitly requires support for token-by-token logprob extraction from **non-streaming** responses.
Streaming support is optional for v1.

Adapters must parse token-level logprobs from full response bodies whenever the provider returns them.
The library must document clearly that **streaming is not required** to use UQ.

### 12.9 Framework and provider integration surface

The implementation must support two classes of integrations:

#### A. Framework/gateway adapters

* LiteLLM
* OpenRouter
* LangChain / LangGraph
* OpenAI Agents SDK

#### B. Direct provider adapters

* OpenAI Chat Completions / Responses
* Gemini
* Fireworks
* Together

Each adapter must:

* normalize request metadata,
* parse selected-token logprobs,
* parse top-k logprobs when present,
* expose structured outputs / tool-call boundaries for segmentation.

### 12.10 LiteLLM integration requirements

LiteLLM should be treated as:

* a transport layer,
* an OpenAI-parameter compatibility layer,
* an optional preflight capability probe surface.

Implementation requirements:

* provide `LiteLLMAdapter.from_response(...)`
* provide `probe_litellm_capability(model, provider=None)` helper when feasible
* detect whether `logprobs` and `top_logprobs` were passed
* detect when unsupported params were dropped or the request failed due to unsupported params

UX rule:

* docs must strongly recommend **not** enabling silent parameter dropping in UQ-critical paths unless the user explicitly wants degraded mode

### 12.11 OpenRouter integration requirements

OpenRouter should be treated as:

* a routing-aware API surface,
* not a guarantee that all routed upstream providers support logprobs equally.

Implementation requirements:

* provide `OpenRouterAdapter.from_response(...)`
* optionally expose `probe_openrouter_model(model)` using the models endpoint when available
* inspect / retain request fields:

  * `logprobs`
  * `top_logprobs`
  * `provider.require_parameters`
  * provider routing metadata when available

Docs must recommend for UQ-enabled runs:

```json
{
  "logprobs": true,
  "top_logprobs": 5,
  "provider": { "require_parameters": true }
}
```

Reason:

* this avoids routing to a backend that silently ignores the requested UQ parameters.

### 12.12 LangChain / LangGraph integration requirements

LangChain/LangGraph integration must be implemented through middleware / wrappers, not custom agent subclasses.

Required deliverables:

* `UQMiddleware` for chat model calls
* `analyze_after_model_call(...)`
* `guard_before_tool_execution(...)`
* LangGraph example showing graph state enriched with `uq_result`

Behavior:

* capture `response.response_metadata["logprobs"]` or provider-equivalent metadata
* attach `UQResult` to the response metadata and optional graph state
* optionally short-circuit tool execution if policy blocks or requests regeneration

### 12.13 OpenAI Agents SDK integration requirements

The OpenAI Agents SDK integration should be minimal and native-feeling.

Required deliverables:

* helper to construct `ModelSettings` with top-logprob settings,
* parser from agent model result / Responses output into `GenerationRecord`,
* optional trace enrichment helper to attach UQ metadata to spans or custom events.

The implementation must not fork or wrap the whole agent runtime.
It should intercept only model outputs and tool execution boundaries.

### 12.14 Direct OpenAI integration requirements

Support both:

* Chat Completions
* Responses API

Adapters must parse:

* selected-token logprobs,
* top-k logprobs,
* structured output boundaries,
* function call names and argument payloads.

OpenAI should be the reference implementation for:

* function calling,
* strict structured outputs,
* argument-level segmentation.

### 12.15 Gemini integration requirements

Gemini adapter must support:

* `responseLogprobs=true` for chosen token logprobs,
* `logprobs=k` for top candidate logprobs,
* non-streaming full-response parsing,
* parsing `logprobsResult` into normalized token records.

If `responseLogprobs` is absent, top-k support is unavailable by definition.
This must be surfaced cleanly in `CapabilityReport`.

### 12.16 Fireworks integration requirements

Fireworks adapter must support:

* OpenAI-compatible chat completions,
* selected-token logprobs,
* `top_logprobs`,
* optional prompt-suffix logprobs when relevant.

### 12.17 Together integration requirements

Together adapter must support:

* selected token list,
* token logprob list,
* `top_logprobs` maps,
* normalization into the common token structure.

### 12.18 Direct provider config recommendations

Each provider/framework integration must document recommended request settings.

#### Canonical / G-NLL mode

Recommended defaults:

```python
UQInferencePreset(
    uq_mode="canonical",
    temperature=0.0,
    top_p=1.0,
    request_logprobs=True,
    request_topk=5,
)
```

Notes:

* `request_topk` is recommended for diagnostics, but selected-token logprobs are the strict requirement.
* if actual runtime settings are anything other than explicit greedy decoding, docs must instruct users to switch to realized mode.

#### Realized mode

Recommended defaults:

```python
UQInferencePreset(
    uq_mode="realized",
    request_logprobs=True,
    request_topk=5,
)
```

Notes:

* use this when actual emitted tokens matter and decoding is sampled or unknown.

### 12.19 Integration ergonomics requirement

The library must feel like a small, clean toolkit.

Acceptable public surface:

```python
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, capability_report)
decision = result.decision
```

Unacceptable public surface:

* deep subclass hierarchies,
* framework-specific analysis code paths embedded into the scorer,
* large provider matrix hardcoded into scoring logic.

## 13. API design

### 13.1 Core analysis API

```python
result = analyzer.analyze_step(record)
```

Returns:

```python
UQResult(
    primary_score,
    primary_score_type,
    mode,
    capability_level,
    capability_report,
    segments=[SegmentResult, ...],
    events=[Event, ...],
    action=PolicyAction,
    diagnostics=Diagnostics,
)
```

### 13.2 Segment result

```python
SegmentResult(
    id,
    kind,
    priority,
    text,
    token_span,
    primary_score,
    metrics,
    events,
    recommended_action,
)
```

### 13.3 Adapter API

Every adapter must implement:

```python
class BaseAdapter(Protocol):
    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord: ...
    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport: ...
```

Optional capability probes:

```python
class CapabilityProbe(Protocol):
    def probe(self, model: str, **kwargs) -> CapabilityProbeResult: ...
```

### 13.4 Framework integration APIs

#### LangChain / LangGraph

```python
wrapped_model = UQMiddleware(chat_model, uq=config)
```

#### Low-level direct usage

```python
record = adapter.capture(resp, request_meta)
result = analyzer.analyze_step(record)
decision = policy.decide(result)
```

### 13.5 Request helpers

The library must include request helper utilities that make it easy to request the right parameters.

Examples:

```python
openai_params = uq.request_params(provider="openai", mode="canonical")
openrouter_params = uq.request_params(provider="openrouter", mode="realized")
gemini_params = uq.request_params(provider="gemini", mode="realized")
```

These helpers must generate provider-appropriate parameter sets.

### 13.6 Documentation requirement for API ergonomics

The implementation must document:

* how to request logprobs for each supported integration,
* how to verify they actually came back,
* how the analyzer behaves under `full`, `selected_only`, and `none` capability tiers,
* how to opt into fail-loud vs degraded mode,
* how to choose canonical vs realized mode.

## 14. Execution policies and developer actions

### 14.1 Action taxonomy

Actions are divided into:

* **annotative**: log / trace / attach metadata
* **regenerative**: regenerate segment or step
* **protective**: block, dry-run, ask confirmation
* **escalative**: human handoff / webhook / pager

### 14.2 Recommended action mapping

#### `continue_with_annotation`

Use when:

* only informational prose is mildly risky,
* no external side effect,
* developers mainly want observability.

#### `regenerate_segment`

Use when:

* a single leaf or clause is risky,
* the rest of the step is acceptable,
* the framework supports structured retry.

#### `retry_step_with_constraints`

Use when:

* tool name or action head is unstable,
* schema adherence failed,
* developer can retry with tighter instructions or lower temperature.

#### `dry_run_verify`

Use when:

* action is executable and externally impactful,
* there is a cheap validator available.
  Examples:
* SQL `EXPLAIN`,
* shell command linting,
* browser action target existence check,
* API argument schema validation.

#### `ask_user_confirmation`

Use when:

* action is destructive or irreversible,
* uncertainty is medium-high but not obviously fatal,
* human confirmation is acceptable latency.

#### `block_execution`

Use when:

* schema invalid,
* required identifier / selector / tool name is highly uncertain,
* destructive action remains risky after retry.

### 14.3 Custom developer actions

The engine supports custom action handlers in userland after `Decision` is returned:

```python
def my_handler(decision: DecisionContext):
    if decision.action == Action.EMIT_WEBHOOK:
        post_to_slack(decision.to_dict())
```

---

## 15. Hardening strategies

### 15.1 Do not score the whole run as one sequence

Always score per invocation and per action-bearing segment.

### 15.2 Use structured outputs and function schemas whenever possible

The product gets much more useful when agent outputs are structurally constrained.
This is both a model-quality best practice and a UQ usability best practice.

### 15.3 Enforce deterministic settings on action steps when possible

Recommended defaults for tool / command / SQL / browser steps:

* `temperature = 0` if supported,
* avoid stochastic exploration for action heads,
* keep user-facing prose separate from executed action generation.

### 15.4 Separate planning from execution

If the framework allows it:

* planning node may be freer,
* execution node should be tightly structured and deterministic.

This improves both reliability and interpretability of UQ signals.

### 15.5 Prefer per-leaf retries over whole-step retries

Local regeneration reduces variance and keeps successful parts stable.

### 15.6 Fail closed on missing capability for critical actions

If a workflow is marked `critical_action` and no logprobs are available, the default policy should allow users to choose `block_without_signal=True`.

---

## 16. Evaluation plan

### 16.1 Product evaluation, not just AUROC

The project should evaluate:

* action blocking precision,
* argument regeneration success rate,
* reduction in failed tool calls,
* reduction in invalid structured outputs reaching executors,
* selective execution performance at fixed coverage,
* latency overhead.

### 16.2 Minimum benchmark set for v1

* structured tool-call benchmark,
* browser action benchmark,
* SQL generation benchmark,
* final-answer ranking benchmark.

### 16.3 Required ablations

* whole-step vs segmented scoring,
* G-NLL vs realized mode on strictly greedy vs non-greedy steps,
* with and without top-k diagnostics,
* per-leaf regeneration vs whole-step retry,
* strict structured outputs vs free-form text.

---

## 17. Implementation plan for coding agent

### 17.1 Repository layout

```text
src/
  agentuq/
    adapters/
      base.py
      openai_chat.py
      openai_responses.py
      openai_agents.py
      litellm.py
      openrouter.py
      langchain.py
      gemini.py
      fireworks.py
      together.py
    probes/
      base.py
      litellm_probe.py
      openrouter_probe.py
    analysis/
      scorer.py
      metrics.py
      entropy.py
      margins.py
      segmentation.py
      events.py
      policy.py
    schemas/
      records.py
      results.py
      config.py
      errors.py
    integrations/
      langchain_middleware.py
      langgraph_hook.py
    docs_assets/
      snippets/
        openai.py
        openrouter.py
        litellm.py
        gemini.py
        fireworks.py
        together.py
        langchain.py
        langgraph.py
        openai_agents.py
    utils/
      json_spans.py
      react_parser.py
      sql_parser.py
      code_spans.py
examples/
  openai_function_call.py
  openrouter_tool_call.py
  litellm_completion.py
  gemini_generate_content.py
  fireworks_chat.py
  together_chat.py
  langchain_wrapper.py
  langgraph_tool_agent.py
  openai_agents_guard.py
docs/
  quickstarts/
    openai.md
    openrouter.md
    litellm.md
    gemini.md
    fireworks.md
    together.md
    langchain.md
    langgraph.md
    openai_agents.md
  concepts/
    capability_tiers.md
    canonical_vs_realized.md
    segmentation.md
    policies.md
    troubleshooting.md
tests/
  ...
```

### 17.2 MVP milestone order

1. config + schemas + errors
2. OpenAI Responses adapter
3. canonical / realized scorers
4. surprise / margin / entropy metrics
5. JSON / tool-call segmentation
6. event engine
7. balanced policy preset
8. OpenAI direct wrapper
9. LiteLLM and OpenRouter adapters
10. LangChain / LangGraph integration wrapper
11. Gemini / Fireworks / Together adapters
12. docs + quickstarts + examples

### 17.3 First release criteria

The first release is done when the repo can:

* analyze an OpenAI function call response,
* analyze one response from each supported direct provider adapter,
* segment the tool name and each argument leaf,
* trigger at least `continue`, `regenerate_segment`, `retry_step_with_constraints`, `ask_user_confirmation`, `block_execution`,
* expose structured results usable by frameworks,
* include at least one end-to-end demo showing a risky tool argument being regenerated before execution,
* include capability-aware docs for every supported integration.

### 17.4 Documentation deliverables are mandatory, not optional

Implementation is incomplete unless documentation ships at the same time.

Required docs for each supported integration:

* quickstart setup,
* how to request logprobs,
* how to request top-k logprobs,
* where token-by-token logprobs appear in the response,
* how to verify capability at runtime,
* how to choose canonical vs realized mode,
* how to interpret degraded mode,
* one working copy-paste example.

### 17.5 Required quickstarts

The repo must include these quickstarts:

* `docs/quickstarts/openai.md`
* `docs/quickstarts/openrouter.md`
* `docs/quickstarts/litellm.md`
* `docs/quickstarts/gemini.md`
* `docs/quickstarts/fireworks.md`
* `docs/quickstarts/together.md`
* `docs/quickstarts/langchain.md`
* `docs/quickstarts/langgraph.md`
* `docs/quickstarts/openai_agents.md`

Each quickstart must contain:

1. install instructions,
2. minimal request with logprobs enabled,
3. `capture -> analyze -> decide` example,
4. sample output excerpt,
5. troubleshooting notes for missing logprobs.

### 17.6 Required provider/framework examples

The repo must ship runnable examples for:

* direct OpenAI function/tool call with strict schema,
* OpenRouter tool-call request with `provider.require_parameters=true`,
* LiteLLM request using logprobs with capability-aware handling,
* Gemini `responseLogprobs` + `logprobs` example,
* Fireworks OpenAI-compatible example,
* Together example,
* LangChain wrapper example,
* LangGraph node/middleware example,
* OpenAI Agents SDK guard example.

### 17.7 Documentation content requirements

#### OpenAI quickstart must show

* how to request logprobs without streaming,
* how to capture function call name and arguments,
* how to use strict structured outputs where relevant,
* how to run canonical vs realized mode.

#### OpenRouter quickstart must show

* why `provider.require_parameters=true` matters,
* how to request `logprobs` and `top_logprobs`,
* how to handle provider routing degradation.

#### LiteLLM quickstart must show

* how to pass logprob parameters,
* how unsupported params fail by default,
* how to avoid accidental silent degradation.

#### Gemini quickstart must show

* `responseLogprobs=true`,
* `logprobs=k`,
* where `logprobsResult` is parsed.

#### Fireworks quickstart must show

* OpenAI-compatible base URL usage,
* `logprobs=True`,
* `top_logprobs=k`.

#### Together quickstart must show

* how `logprobs=k` is requested,
* where tokens, token logprobs, and top_logprobs are found.

#### LangChain / LangGraph quickstarts must show

* model binding for logprobs,
* middleware / wrapper approach,
* policy-triggered tool blocking or regeneration.

#### OpenAI Agents quickstart must show

* how model settings are configured,
* how UQ integrates with agent output and tool boundaries,
* optional trace enrichment.

### 17.8 Troubleshooting docs are mandatory

`docs/concepts/troubleshooting.md` must cover at minimum:

* requested logprobs but response omitted them,
* top-k unavailable,
* canonical mode requested on non-greedy or unknown-decoding runs,
* OpenRouter route ignored unsupported parameters,
* LiteLLM unsupported parameter behavior,
* provider returned structure but no token details,
* how to force fail-loud mode.

### 17.8.1 Testing strategy for public OSS

The repo should use a three-tier testing strategy:

* `tests/unit` for deterministic offline tests,
* `tests/contracts` for sanitized real-payload fixture coverage,
* `tests/live` for optional manual smoke tests with local API keys.

Rules:

* live tests are optional and manually triggered,
* live tests are not part of required public OSS CI,
* live tests exist to detect API drift and verify example integration paths,
* live tests must not assert exact score values or exact output text,
* contract fixtures are the preferred offline mechanism for payload-shape regression coverage.

### 17.9 Concept docs are mandatory

Required concept docs:

* `public_api.md`
* `provider_capabilities.md`
* `reading_results.md`
* `capability_tiers.md`
* `canonical_vs_realized.md`
* `acting_on_decisions.md`
* `research_grounding.md`
* `segmentation.md`
* `policies.md`
* `troubleshooting.md`

`canonical_vs_realized.md` must explain plainly:

* when G-NLL is valid,
* when realized-path NLL is required,
* why these are different objects,
* why the library switches modes.

## 18. README positioning copy

### One-line description

Single-pass runtime reliability instrumentation for LLM agents using token logprobs.

### Plain-language framing

This library does not claim to know whether an output is “true.” It gives agent developers a cheap, structured way to identify risky steps, localize brittle spans, and connect that signal to concrete runtime actions like retrying, regenerating, blocking, or asking for user confirmation.

### Honest promise

Best for:

* strictly greedy agent steps for canonical scoring,
* structured outputs and tool arguments,
* teams that already have validators, retries, and human-in-the-loop paths.

Not a replacement for:

* retrieval,
* external verification,
* task-specific validators,
* human review in high-stakes domains.

---

## 19. Final product decision

The product should ship as:

* **an agent reliability layer**,
* built around **mode-aware probability scoring**,
* with **G-NLL as the canonical flagship method**,
* and **realized-path diagnostics as the truthful fallback** when G-NLL assumptions do not hold.

That gives the project a rigorous research anchor, honest product framing, and clear runtime value inside real agent frameworks.
