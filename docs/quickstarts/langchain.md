# LangChain Quickstart

Use a wrapper around the chat model rather than a custom subclass.

## Install

```bash
pip install langchain langchain-openai
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from langchain_openai import ChatOpenAI
from uq_runtime.integrations.langchain_middleware import UQMiddleware
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.results import UQResult

config = UQConfig(policy="balanced", tolerance="strict")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0.0).bind(logprobs=True, top_logprobs=5)
wrapped = UQMiddleware(model, config)
response = wrapped.invoke(
    "Return the single word Paris.",
    config={"metadata": {"top_p": 1.0, "deterministic": True}},
)
result = UQResult.model_validate(response.response_metadata["uq_result"])
print(result.pretty())
```

## Notes

- AgentUQ expects token logprobs to appear under `response.response_metadata["logprobs"]` or provider-equivalent metadata.
- `UQMiddleware` infers request metadata from bound LangChain/OpenAI model settings when you do not pass `config.metadata`.
- For tool calling, AgentUQ prefers LangChain's standardized `response.tool_calls` field and falls back to provider-specific `additional_kwargs`.
- On OpenAI-compatible LangChain models, tool calls are structural metadata; AgentUQ will not infer token-grounded `tool_name` or `tool_argument_leaf` spans unless the provider actually returns grounded spans.
- Attach the resulting `uq_result` to traces or downstream state if the step can trigger tools.

## Sample output excerpt

```text
Summary
  mode: canonical
  reason: auto-selected canonical mode from strict greedy parameter inference
  aggregate_primary_score: 0.025 g_nll
  action: continue
  rationale: Policy preset balanced selected continue based on segment events.
  capability: full

Segments
  final_answer_text [informational] -> continue
    text: Paris.
    metrics: score=0.025 avg_surprise=0.013 max_surprise=0.019 mean_entropy=0.108
    events: none
```

## Troubleshooting

- Bind logprob params on the model before wrapping it. Explicit `config={"metadata": ...}` still overrides inferred values when you need to force a specific request surface.
- If your provider adapter stores token metadata elsewhere, pass a custom `request_meta` map and normalize before analysis.
- LangChain live checks are optional local smoke tests only.
