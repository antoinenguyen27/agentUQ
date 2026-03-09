# Fireworks Quickstart

Fireworks exposes chat completions with an OpenAI-compatible `choices[0].logprobs.content` shape when you request `logprobs=True`, with compatibility fallbacks for older token-array payloads.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request

```python
from openai import OpenAI
from uq_runtime.adapters.fireworks import FireworksAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key="...")
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=[{"role": "user", "content": "Return a SQL query for active users"}],
    logprobs=True,
    top_logprobs=5,
    temperature=0.0,
)

adapter = FireworksAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
request_meta = {"model": "accounts/fireworks/models/llama-v3p1-8b-instruct", "logprobs": True, "top_logprobs": 5, "deterministic": True}
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.action)
```

## Sample output excerpt

```text
segment=sql_clause action=dry_run_verify
```

## Troubleshooting

- Request `logprobs=True` and `top_logprobs=k`.
- AgentUQ prefers the OpenAI-compatible `choices[0].logprobs.content` format, and falls back to legacy token arrays or `raw_output.completion_logprobs` when needed.
- In this OSS repo, live Fireworks checks are manual and opt-in.
