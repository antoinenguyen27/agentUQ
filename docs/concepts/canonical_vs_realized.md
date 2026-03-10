# Canonical Vs Realized

AgentUQ exposes two different probability objects and does not blur them.

## Canonical mode

Canonical mode uses `G-NLL`, the negative log-likelihood of the greedy generation path. Use it only when the step is explicitly known to be greedy.

Recommended conditions:

- `temperature == 0`
- `top_p == 1`
- step metadata marks the call as deterministic

Current implementation will also auto-select canonical mode when strict greedy parameters are present and deterministic metadata is absent. The recorded `Diagnostics.mode_reason` distinguishes explicit metadata from parameter inference even though the default human-readable rendering keeps the summary focused on action-driving output.

## Realized mode

Realized mode uses realized-path NLL on the actual emitted sequence. This is the correct mode when decoding was sampled or when runtime metadata is unknown.

Realized mode is also the right operational lens for action-bearing spans such as tool arguments, selectors, URLs, and SQL clauses because the emitted value is what will be executed.

Low-temperature or otherwise near-deterministic runs still belong to realized mode unless you can prove the emitted sequence was the greedy path. They may be closer operational proxies to greedy decoding, but they are not `G-NLL`.

## Why this matters

Treating a sampled trajectory, or a merely low-temperature trajectory, as if its local top-1 alternatives under sampled prefixes were a true canonical greedy path is not valid `G-NLL`. AgentUQ refuses to do that.
