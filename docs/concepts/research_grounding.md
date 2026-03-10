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
