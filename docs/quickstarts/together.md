# Together Quickstart

Together chat completions return token lists, token logprobs, and top-logprob maps under `choices[0].logprobs`.

## Install

```bash
pip install together
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from together import Together
from uq_runtime.adapters.together import TogetherAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = Together(api_key="...")
request_meta = {
    "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "logprobs": 5,
    "temperature": 0.0,
    "top_p": 1.0,
    "deterministic": True,
}
response = client.chat.completions.create(
    model=request_meta["model"],
    messages=[{"role": "user", "content": "Return a browser command to click submit."}],
    logprobs=request_meta["logprobs"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = TogetherAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Sample output excerpt

```text
Summary
  mode: canonical
  reason: auto-selected canonical mode from strict greedy parameter inference
  aggregate_primary_score: 2.933 g_nll
  action: continue
  rationale: Policy preset balanced selected continue based on segment events.
  capability: full

Segments
  browser_action [critical_action] -> continue
    text: click("text=Submit")
    metrics: score=2.933 avg_surprise=0.367 max_surprise=1.144 mean_entropy=0.883
    events: none
```

## Troubleshooting

- Together uses `logprobs=k` rather than separate `top_logprobs`.
- Verify that `choices[0].logprobs` includes `tokens`, `token_logprobs`, and `top_logprobs`.
- Together-backed smoke checks should be run locally with your own API key, not in required CI.
