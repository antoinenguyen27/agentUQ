---
title: Research Grounding
description: The narrower claims AgentUQ makes about token probabilities, sequence likelihood, and operational localization.
slug: /concepts/research-grounding
sidebar_position: 9
---

# Research Grounding

AgentUQ is designed to be academically honest and operationally useful.

The core idea is simple:

- start from standard autoregressive likelihood objects that language models already expose through token logprobs,
- choose the right probability object for the decoding regime,
- localize that signal onto the spans that matter operationally,
- and use policy to decide when a cheap intervention is enough and when a more expensive verifier is worth invoking.

## What AgentUQ is claiming

AgentUQ does **not** claim to estimate truth directly.

It does claim to provide a useful runtime risk signal for agent systems:

- cheap enough to run on every step,
- grounded in native model probabilities rather than prompted self-confidence,
- localized to action-bearing spans rather than only whole-response summaries,
- and directly connected to concrete control actions.

That is a narrower claim than "hallucination detection," but it is a stronger and more defensible one.

## The probability objects

For an emitted token sequence `y_1 ... y_T` conditioned on context `x`, the standard autoregressive quantity is:

```text
NLL(y | x) = Σ_t -log p(y_t | x, y_<t)
```

AgentUQ uses two mode-correct variants of this same family:

- `G-NLL` for explicitly greedy runs when the emitted path is known to be the greedy path
- realized-path NLL for sampled or unknown-decoding runs on the actual emitted tokens

This is the key statistical discipline in the system. AgentUQ does not score sampled trajectories as if they were greedy.

For the greedy-path case specifically, recent work argues that this style of sequence-level likelihood deserves more attention as a central UQ object in LLMs: [Aichberger et al. 2026](https://arxiv.org/abs/2412.15176v2).

## Why segmentation is mathematically honest

Segmentation is not a replacement for the underlying math. It is a localization step.

When non-overlapping leaf segments partition the emitted tokens, the whole-response NLL decomposes additively over those leaves:

```text
NLL(step) = Σ_i NLL(segment_i)
```

That means AgentUQ is not inventing a separate uncertainty object for SQL, tool arguments, selectors, or prose spans. It is attributing the same emitted-path likelihood to the spans that matter operationally.

This is why segmentation is so important for agents:

- whole-response scoring tells you that something in the step looked brittle
- segment-level scoring tells you whether the brittleness was in prose, a selector, a URL, a shell flag, or an SQL clause

For agent control, that difference is the difference between "interesting metric" and "actionable runtime signal."

## Where AgentUQ sits in the reliability stack

AgentUQ is deliberately positioned between no gate and expensive verification.

- No gate: cheapest, fastest, highest risk
- AgentUQ: single-pass, provider-native, localized runtime gate
- Judge model, semantic verifier, retrieval, sandbox execution, or human review: higher-cost, slower, often higher-precision checks

The intended workflow is selective escalation:

- let AgentUQ run on every step
- use it to catch brittle or ambiguous spans cheaply
- invoke slower verification only when the local signal says the step is risky enough to justify the cost

## Why this still matters when models hallucinate confidently

High-confidence hallucinations are real. That does not invalidate AgentUQ.

It defines the boundary of what the method is for.

AgentUQ is strongest when:

- the output contains structured or action-bearing spans,
- the system needs a cheap black-box signal,
- the developer wants to rank or gate steps rather than prove correctness,
- and the runtime already has retry, dry-run, confirmation, or verification hooks.

AgentUQ is weaker when:

- the error is semantically wrong but still locally high-probability,
- the task requires deep factual verification rather than local runtime risk detection,
- or the output is long-form and stylistically variable in ways that dominate likelihood.

So the right claim is not "logprobs catch all hallucinations."

The right claim is:

AgentUQ cheaply catches many brittle or ambiguous steps, especially in structured agent workflows, and tells you when the run is risky enough to justify a slower second layer.

## Why not use a stronger method by default

There are stronger uncertainty methods for some tasks.

For example, semantic-entropy-style approaches can detect meaning-level inconsistency more effectively in many hallucination settings. But they usually require multiple generations, clustering or semantic comparison, and a materially larger runtime budget.

That is a different operating point from AgentUQ.

AgentUQ is intentionally optimized for:

- single-pass runtime use,
- black-box provider compatibility,
- low latency and low cost,
- and direct integration into agent control flows.

## Common questions

### Isn't this just perplexity?

It uses the same likelihood family, but it plays a different role.

Perplexity is usually treated as a whole-sequence quality summary. AgentUQ uses mode-correct sequence likelihood as runtime telemetry, adds local token diagnostics, and then localizes the signal onto action-bearing spans so the result can drive control actions.

That is the important difference:

- whole-answer summary metric
- versus step-level runtime control signal

See also [Canonical vs realized](canonical_vs_realized.md) and [Segmentation](segmentation.md).

### Why should logprobs mean anything?

Because they are the model's own conditional preference signal over the tokens it emitted.

That does not make them a truth oracle. It does make them a useful black-box signal for where generation looked brittle, ambiguous, or locally unstable.

This is exactly the kind of signal you want for cheap runtime gating:

- where should I retry?
- where should I verify?
- where should I avoid executing yet?

### If models can hallucinate confidently, why is this still useful?

Because the right comparison is not "AgentUQ versus a perfect verifier." The right comparison is:

- no gate,
- a cheap first-pass gate,
- or a slower second layer such as retrieval-backed verification, semantic checking, sandboxing, an LLM judge, or human review.

AgentUQ is useful because it improves substantially over no gate while remaining cheap enough to run everywhere. When it finds a brittle or ambiguous step, it can trigger a slower layer selectively instead of paying that cost on every step.

### Why do you insist on greedy mode for G-NLL?

Because `G-NLL` is supposed to describe the greedy path.

Once the run is sampled, or once decoding metadata is unknown, you are no longer scoring the canonical greedy answer. The honest probability object is the realized emitted path. That is why AgentUQ treats canonical and realized mode as different objects rather than small variations of the same number.

See [Canonical vs realized](canonical_vs_realized.md).

### Does segmentation break the math?

No. Segmentation is a localization step, not a new scoring family.

For non-overlapping leaf segments, the emitted-path likelihood of the whole step decomposes over those leaves. That means AgentUQ is not inventing separate probabilities for SQL, selectors, or prose; it is attributing one emitted-path likelihood object to smaller operational units.

That is what turns a blunt whole-answer score into a useful control signal.

### Are segment scores independent?

No.

Each segment is still conditioned on the prompt and the tokens that came before it. A risky SQL clause and the prose before it are part of one autoregressive path, not separate independent random variables.

So segment scores should be read as local diagnostics, not independent beliefs.

### Why not use semantic entropy or another stronger hallucination method?

Because the best method depends on the operating point you care about.

Semantic entropy can be stronger for meaning-level inconsistency and hallucination detection, but it usually needs multiple generations and extra semantic comparison. AgentUQ is optimized for a cheaper operating point:

- single pass
- black-box provider compatibility
- low latency
- direct actionability in agent loops

That tradeoff is intentional, not accidental.

### What is AgentUQ actually good at?

It is strongest when local uncertainty has an obvious operational consequence.

Examples:

- a tool argument that may be invalid
- a selector that might target the wrong element
- a URL or path that might be malformed
- an SQL clause that should be validated before execution
- prose that looks shaky enough to annotate or verify

These are the places where a localized signal is more useful than a global "confidence" score.

### What should I do with the result?

Treat it as a routing signal for the next step in your system.

Examples:

- `continue`: proceed normally
- `continue_with_annotation`: continue, but attach the result to logs or traces
- `regenerate_segment`: repair one risky field or clause
- `retry_step_with_constraints`: reprompt the agent with tighter instructions, lower temperature, or stronger schema reminders
- `dry_run_verify`: run `EXPLAIN`, lint, schema validation, selector existence checks, or similar safe validators
- `ask_user_confirmation`: interrupt before a side effect
- `block_execution`: fail closed

In retrieval-heavy systems, another valid response is to fetch more context and rerun the step with stronger grounding.

See [Acting on decisions](acting_on_decisions.md).

### How should I tune the system?

Start with the coarse knobs first.

- `policy` changes what AgentUQ tends to do after it sees risk
- `tolerance` changes how easily events are emitted
- `thresholds` fine-tune individual metric cutoffs
- `custom_rules` override one specific segment/event case without changing the whole preset

In practice:

- if the system is too passive, try a stricter policy or stricter tolerance
- if it is too noisy, start by relaxing tolerance before editing raw numbers
- only tune thresholds when you already know which metric is responsible
- use custom rules when your defaults are broadly right but one span type has a sharper requirement

See [Policies](policies.md) and [Tolerance](tolerance.md).

## Research map

- [Aichberger et al. 2026](https://arxiv.org/abs/2412.15176v2): revisits greedy-path negative log-likelihood as a first-class uncertainty object for LLMs
- [Kumar et al. 2024](https://aclanthology.org/2024.acl-long.20/): token probabilities are meaningfully aligned with model confidence, though not perfectly calibrated correctness estimates
- [Lin et al. 2024](https://aclanthology.org/2024.emnlp-main.578/): raw sequence likelihood is useful but does not fully solve token-importance and wording-sensitivity problems on its own
- [Vazhentsev et al. 2025](https://aclanthology.org/2025.naacl-long.113/): local token uncertainty remains useful for generation-time confidence and ranking
- [Farquhar et al. 2024](https://www.nature.com/articles/s41586-024-07421-0): stronger meaning-level hallucination detection is possible with semantic entropy, but at a meaningfully higher runtime cost

## Recommended mental model

Do not read AgentUQ as "AI truth scoring."

Read it as:

single-pass runtime reliability telemetry for agent steps, grounded in sequence likelihood, localized by segmentation, and made actionable by policy.
