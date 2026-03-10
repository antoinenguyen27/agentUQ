# LangChain Quickstart

Use a wrapper around the chat model rather than a custom subclass.

## Install

```bash
pip install langchain langchain-openai
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from agentuq import UQConfig, UQResult
from agentuq.integrations.langchain_middleware import UQMiddleware
from langchain_openai import ChatOpenAI

config = UQConfig(policy="balanced", tolerance="strict")
model = ChatOpenAI(model="gpt-4o-mini", temperature=0.0).bind(logprobs=True, top_logprobs=5)
wrapped = UQMiddleware(model, config)
response = wrapped.invoke(
    "Return the single word Paris.",
    config={"metadata": {"top_p": 1.0}},
)
result = UQResult.model_validate(response.response_metadata["uq_result"])
print(result.pretty())
```

## Notes

- AgentUQ expects token logprobs to appear under `response.response_metadata["logprobs"]` or provider-equivalent metadata.
- `UQMiddleware` infers request metadata from bound LangChain/OpenAI model settings when you do not pass `config.metadata`.
- For canonical mode, AgentUQ only needs the strict greedy settings to be visible in the captured metadata. You do not need a synthetic `deterministic` flag.
- For tool calling, AgentUQ prefers LangChain's standardized `response.tool_calls` field and falls back to provider-specific `additional_kwargs`.
- On OpenAI-compatible LangChain models, tool calls are structural metadata; AgentUQ will not infer token-grounded `tool_name` or `tool_argument_leaf` spans unless the provider actually returns grounded spans.
- Attach the resulting `uq_result` to traces or downstream state if the step can trigger tools.

## Sample output excerpt

```text
Summary
  recommended_action: Continue
  rationale: Policy preset balanced selected continue based on segment events.
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

- Bind logprob params on the model before wrapping it. Explicit `config={"metadata": ...}` still overrides inferred values when you need to force a specific request surface.
- If your provider adapter stores token metadata elsewhere, pass a custom `request_meta` map and normalize before analysis.
- LangChain live checks are optional local smoke tests only.
