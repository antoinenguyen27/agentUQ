# LangChain Quickstart

Use a wrapper around the chat model rather than a custom subclass.

## Install

```bash
pip install langchain langchain-openai
pip install -e .[dev]
```

## Minimal request

```python
from langchain_openai import ChatOpenAI
from uq_runtime.integrations.langchain_middleware import UQMiddleware
from uq_runtime.schemas.config import UQConfig

model = ChatOpenAI(model="gpt-4o-mini").bind(logprobs=True, top_logprobs=5)
wrapped = UQMiddleware(model, UQConfig(policy="balanced", tolerance="strict"))
response = wrapped.invoke("Return a tool call for weather in Paris")
print(response.response_metadata["uq_result"]["action"])
```

## Notes

- AgentUQ expects token logprobs to appear under `response.response_metadata["logprobs"]` or provider-equivalent metadata.
- Attach the resulting `uq_result` to traces or downstream state if the step can trigger tools.

## Sample output excerpt

```text
response.response_metadata["uq_result"]["action"] == "regenerate_segment"
```

## Troubleshooting

- Bind logprob params on the model before wrapping it.
- If your provider adapter stores token metadata elsewhere, pass a custom `request_meta` map and normalize before analysis.
- LangChain live checks are optional local smoke tests only.
