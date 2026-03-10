# Fireworks Quickstart

Fireworks exposes chat completions with an OpenAI-compatible `choices[0].logprobs.content` shape when you request `logprobs=True`, with compatibility fallbacks for older token-array payloads.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from openai import OpenAI
from uq_runtime.adapters.fireworks import FireworksAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key="...")
request_meta = {
    "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
    "logprobs": True,
    "top_logprobs": 5,
    "temperature": 0.0,
    "top_p": 1.0,
    "deterministic": True,
}
response = client.chat.completions.create(
    model=request_meta["model"],
    messages=[{"role": "user", "content": "Return a SQL query for active users."}],
    logprobs=request_meta["logprobs"],
    top_logprobs=request_meta["top_logprobs"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = FireworksAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Sample output excerpt

```text
Summary
  recommended_action: Dry-run verify
  rationale: Policy preset balanced selected dry_run_verify based on segment events.
  mode: canonical
  whole_response_score: 3.844 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  SQL clause [critical_action] -> Dry-run verify
    text: WHERE active = true
    surprise: score=1.922 nll=1.922 avg=0.641 p95=4.182 max=4.182 tail=4.182
    events:
      - LOW_PROB_SPIKE [high]: Highly improbable token spike detected. (max_surprise=4.182 >= spike_surprise=3.500)
```

## Troubleshooting

- Request `logprobs=True` and `top_logprobs=k`.
- AgentUQ prefers the OpenAI-compatible `choices[0].logprobs.content` format, and falls back to legacy token arrays or `raw_output.completion_logprobs` when needed.
- In this OSS repo, live Fireworks checks are manual and opt-in.
