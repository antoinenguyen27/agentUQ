# Fireworks Quickstart

Fireworks exposes OpenAI-compatible chat completions. AgentUQ reuses the shared OpenAI-style adapter.

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

client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key="...")
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=[{"role": "user", "content": "Return a SQL query for active users"}],
    logprobs=True,
    top_logprobs=5,
    temperature=0.0,
)

adapter = FireworksAdapter()
request_meta = {"model": "accounts/fireworks/models/llama-v3p1-8b-instruct", "logprobs": True, "top_logprobs": 5, "deterministic": True}
record = adapter.capture(response, request_meta)
result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
print(result.action)
```

## Sample output excerpt

```text
segment=sql_clause action=dry_run_verify
```

## Troubleshooting

- Fireworks is OpenAI-compatible here; request `logprobs=True` and `top_logprobs=k`.
- If token details are missing, inspect the raw response body before assuming support.
