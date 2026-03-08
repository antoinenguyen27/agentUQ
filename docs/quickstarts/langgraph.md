# LangGraph Quickstart

Use wrapper and hook functions around model nodes, then interrupt before tool execution when policy demands it.

## Install

```bash
pip install langgraph langchain-openai
pip install -e .[dev]
```

## Minimal pattern

```python
from uq_runtime.schemas.config import UQConfig
from uq_runtime.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool

config = UQConfig(policy="conservative", tolerance="strict")
state = enrich_graph_state(state, model_response, config)
if should_interrupt_before_tool("weather_lookup", state):
    # route to retry, user confirmation, or human handoff
    ...
```

## Notes

- Treat each model node invocation as one `GenerationRecord`.
- Attach `uq_result` to graph state before any tool node with side effects.

## Sample output excerpt

```text
should_interrupt_before_tool("weather_lookup", state) == True
```

## Troubleshooting

- If tool execution is not being interrupted, inspect the stored `uq_result` and segment actions in graph state.
- Keep tool nodes separate from model nodes so AgentUQ can gate side effects cleanly.
- LangGraph-backed smoke checks are local-only and not a required contribution gate.
