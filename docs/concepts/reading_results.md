---
title: Reading Results
description: How to interpret AgentUQ summaries, segment metrics, triggered events, and threshold comparisons.
slug: /concepts/reading-results
sidebar_position: 2
---

# Reading Results

AgentUQ results are designed to answer two questions quickly:

1. what is the recommended action for this step?
2. which exact span made that action necessary?

## Start with the summary

The summary gives the step-level picture:

- `recommended_action`: what the policy wants you to do next
- `rationale`: why that action was chosen
- `mode`: `canonical` or `realized`
- `whole_response_score`: likelihood summary for the entire emitted path
- `capability`: whether top-k diagnostics were available

The most important rule:

`whole_response_score` is a whole-step summary, not the thing that directly determines the recommended action.

The action comes from segment-level events and policy mapping.

## Then read the risk summary

The risk summary tells you which segment actually drove the recommendation:

- `decision_driving_segment`
- `decision_driver_type`
- `decision_driving_segments`
- `decision_driver_preview`

Use this section as your pointer to the operationally relevant span.

If the driver is informational prose only, that usually means:

- annotate
- maybe retry in high-trust workflows
- do not treat it like a risky executable span unless action-bearing segments also triggered

## Then inspect the segments

Each segment gives you:

- its kind, such as `sql_clause`, `browser_selector`, or `final_answer_text`
- its priority, such as `critical_action` or `informational`
- its recommended action
- a text preview
- grouped metrics
- triggered events

This is the level where you decide whether to repair one field, retry the whole step, run a validator, or stop before a side effect.

## What the metric groups mean

### Surprise

This is the likelihood view over the emitted tokens in the segment.

- `score` / `nll`: total negative log-likelihood for the segment
- `avg`: average token surprise
- `p95`: high-end surprise among tokens in the segment
- `max`: single most surprising token
- `tail`: mean surprise over the riskiest tokens in the segment

Intuition:

- high total surprise can come from a long segment
- high `max` or `tail` often points to a sharp local issue

### Margin

Margin measures how clearly the model separated the emitted token from the nearest alternative.

- high margin: the model had a clear local preference
- low margin: the local choice was close and potentially brittle

The most useful margin fields are:

- `mean`
- `min`
- `low_margin_rate`
- `low_margin_run_max`

Repeated low margin is often more informative than one isolated token.

### Entropy

Entropy measures how diffuse the top-k token distribution looked.

- low entropy: concentrated distribution
- high entropy: many plausible local alternatives

In AgentUQ this is an approximate top-k view, not a full-vocabulary entropy.

### Rank

Rank is mainly relevant in realized mode when top-k is available.

It tells you whether the emitted token repeatedly diverged from local top-1 or even fell outside the returned top-k candidates.

This is useful for spotting sampled-path instability.

## What the events mean

Events translate raw metrics into interpretable runtime signals.

Common examples:

- `LOW_MARGIN_CLUSTER`: the model repeatedly had trouble separating nearby choices
- `HIGH_ENTROPY_CLUSTER`: the local token distribution stayed diffuse
- `LOW_PROB_SPIKE`: one token or field was highly improbable
- `TAIL_RISK_HEAVY`: several unusually improbable tokens accumulated in one span
- `ACTION_HEAD_UNCERTAIN`: the action choice itself looked unstable
- `ARGUMENT_VALUE_UNCERTAIN`: a leaf value looked brittle
- `SCHEMA_INVALID`: structured output failed validation

The event code matters more than the raw metric alone because policy acts on events, not just on totals.

## What thresholds are for

In debug views, thresholds show why an event fired.

Examples:

- observed `low_margin_rate` versus the configured threshold
- observed `max_surprise` versus the spike threshold
- observed `off_top1_rate` versus the rank threshold

Thresholds are useful for tuning, but most users should first choose a better `policy` or `tolerance` preset rather than editing raw numbers.

See [Tolerance](tolerance.md) and [Policies](policies.md).

## What to compare, and what not to compare

Good comparisons:

- segments within the same step
- the same workflow shape across repeated runs
- event patterns under different tolerance/policy settings

Comparisons to treat cautiously:

- raw whole-response scores across different models
- raw scores across very different prompts or tasks
- long prose segments versus short action spans without looking at normalized metrics and events

Use segment scores primarily for localization and routing inside a workflow, not as a universal benchmark.

## A good reading order in practice

1. `recommended_action`
2. `decision_driving_segment`
3. the driving segment's events
4. the driving segment's text preview
5. only then the supporting metric groups and thresholds

This order keeps the focus on actionability instead of over-reading the raw numbers.

## Common mistakes

- Treating `whole_response_score` as the reason for the action
- Treating prose-only warnings as equivalent to risky executable text
- Comparing raw scores across unrelated tasks or models
- Reading segment scores as independent probabilities
- Jumping to threshold tuning before trying a different `policy` or `tolerance`

For full routing guidance, see [Acting on decisions](acting_on_decisions.md). For the statistical framing, see [Research grounding](research_grounding.md).
