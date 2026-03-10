# Capability Tiers

AgentUQ reports the observed token-logprob capability of each generation.

- `full`: selected-token logprobs and top-k logprobs were returned. Entropy, margin, and rank diagnostics are available.
- `selected_only`: selected-token logprobs were returned but top-k was not. Primary NLL scoring still works, but entropy and rank events degrade and `MISSING_TOPK` is emitted.
- `none`: no usable token logprobs were returned. By default AgentUQ fails loudly if logprobs were required.

The capability decision uses three inputs in order:

1. Provider-declared support when available
2. Requested parameters
3. Observed response payload

This keeps the runtime honest when a gateway accepts a parameter but does not actually return the requested structure.

For provider- and framework-specific expectations, see [Provider and framework capabilities](provider_capabilities.md).
