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
from agentuq import Analyzer, UQConfig
from agentuq.adapters.together import TogetherAdapter

client = Together(api_key="...")
request_meta = {
    "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "logprobs": 5,
    "temperature": 0.0,
    "top_p": 1.0,
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
  recommended_action: Continue
  rationale: Policy preset balanced selected continue based on segment events.
  mode: canonical
  whole_response_score: 2.933 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  browser action [critical_action] -> Continue
    text: click("text=Submit")
    surprise: score=2.933 nll=2.933 avg=0.367 p95=1.144 max=1.144 tail=1.144
    events: none
```

## Troubleshooting

- Together uses `logprobs=k` rather than separate `top_logprobs`.
- Verify that `choices[0].logprobs` includes `tokens`, `token_logprobs`, and `top_logprobs`.
- Together-backed smoke checks should be run locally with your own API key, not in required CI.
