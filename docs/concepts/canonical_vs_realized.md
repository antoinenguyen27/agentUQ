---
title: Canonical Vs Realized
description: When to use greedy-path G-NLL versus realized-path scoring, and why AgentUQ refuses to blur the two.
slug: /concepts/canonical-vs-realized
sidebar_position: 7
---

# Canonical Vs Realized

AgentUQ exposes two different probability objects and does not blur them.

This distinction is not product polish. It is a statistical requirement.

## Canonical mode

Canonical mode uses `G-NLL`, the negative log-likelihood of the greedy generation path. Use it only when the step is explicitly known to be greedy.

Recommended conditions:

- `temperature == 0`
- `top_p == 1`
- request/capture metadata keeps those greedy settings visible at analysis time

If AgentUQ cannot establish those strict greedy settings from the captured metadata, `auto` mode will use realized mode instead.

## Realized mode

Realized mode uses realized-path NLL on the actual emitted sequence. This is the correct mode when decoding was sampled or when runtime metadata is unknown.

Realized mode is also the right operational lens for action-bearing spans such as tool arguments, selectors, URLs, and SQL clauses because the emitted value is what will be executed.

Low-temperature or otherwise near-deterministic runs still belong to realized mode unless you can prove the emitted sequence was the greedy path. They may be closer operational proxies to greedy decoding, but they are not `G-NLL`.

## Why this matters

Treating a sampled trajectory, or a merely low-temperature trajectory, as if its local top-1 alternatives under sampled prefixes were a true canonical greedy path is not valid `G-NLL`. AgentUQ refuses to do that.

At a practical level:

- canonical mode answers: "how likely was the model's canonical greedy output?"
- realized mode answers: "how surprising was the actual emitted output?"

Those are both useful, but they are not interchangeable.

For agent systems, that matters most on executed text. If the model emitted a tool argument, selector, URL, or SQL clause that will actually be used, the realized emitted value is the operational object that must be scored and potentially verified.
