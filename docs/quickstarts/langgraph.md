# LangGraph Quickstart

Use wrapper and hook functions around model nodes, then gate the workflow before side effects. The default safe pattern is to attach `uq_result` after the model node and branch on `result.decision.action`; `should_interrupt_before_tool(...)` is a narrower helper for explicitly grounded tool spans.

## Install

```bash
pip install langgraph langchain-openai
pip install -e .[dev]
```

## Minimal pattern with readable terminal output

```python
from agentuq import UQConfig, UQResult
from agentuq.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from langchain_openai import ChatOpenAI

config = UQConfig(policy="conservative", tolerance="strict")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0.0).bind(logprobs=True, top_logprobs=5)
response = model.invoke("Return the single word Paris.")
state = enrich_graph_state({}, response, config, {"top_p": 1.0})
result = UQResult.model_validate(state["uq_result"])
print(result.pretty())
print(f"should_interrupt_before_tool('weather_lookup'): {should_interrupt_before_tool('weather_lookup', state)}")
```

## Notes

- Treat each model node invocation as one `GenerationRecord`.
- Attach `uq_result` to graph state before any tool node with side effects.
- Treat `result.decision.action` as the default guard before tool execution or any external action.
- OpenAI-compatible framework responses usually expose tool calls structurally but not token-grounded tool-call logprobs, so `should_interrupt_before_tool(...)` only trips when AgentUQ has an explicit grounded tool segment.

## Beyond boolean interruption

`should_interrupt_before_tool(...)` is the narrowest built-in guard. Use it only when the provider/framework path preserves explicit grounding for the tool span. If you want fuller behavior, read the stored `UQResult` from state and branch on `result.decision.action` directly.

That is the right pattern when you want to:

- retry a model node,
- dry-run verify a generated action,
- attach annotation metadata without interrupting the graph,
- or route risky steps to a confirmation node.

## Sample output excerpt

```text
Summary
  recommended_action: Continue
  rationale: Policy preset conservative selected continue based on segment events.
  mode: canonical
  whole_response_score: 0.025 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  final answer prose [informational] -> Continue
    text: Paris.
    surprise: score=0.025 nll=0.025 avg=0.013 p95=0.019 max=0.019 tail=0.019
    events: none
```

## Troubleshooting

- If tool execution is not being interrupted, inspect the stored `uq_result` and segment actions in graph state.
- Keep tool nodes separate from model nodes so AgentUQ can gate side effects cleanly.
- For full action routing rather than `True`/`False` interruption, load the stored `UQResult` and branch on `result.decision.action`.
- LangGraph-backed smoke checks are local-only and not a required contribution gate.
