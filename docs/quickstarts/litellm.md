# LiteLLM Quickstart

LiteLLM is treated as a transport and compatibility layer, not as a separate scoring path.

## Install

```bash
pip install litellm
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from litellm import completion
from agentuq import Analyzer, UQConfig
from agentuq.adapters.litellm import LiteLLMAdapter

request_meta = {
    "model": "openai/gpt-4o-mini",
    "logprobs": True,
    "top_logprobs": 5,
    "drop_params": False,
    "temperature": 0.0,
    "top_p": 1.0,
}
response = completion(
    model=request_meta["model"],
    messages=[{"role": "user", "content": "Return JSON for the weather in Paris."}],
    logprobs=request_meta["logprobs"],
    top_logprobs=request_meta["top_logprobs"],
    drop_params=request_meta["drop_params"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = LiteLLMAdapter()
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
  whole_response_score: 1.204 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  JSON value [important_action] -> Continue
    text: Paris
    surprise: score=0.411 nll=0.411 avg=0.205 p95=0.310 max=0.310 tail=0.310
    events: none
```

## Troubleshooting

- Prefer `drop_params=False` in UQ-critical paths.
- If you can collect `supported_openai_params`, pass them into `request_meta` so capability reporting is explicit.
- Use this path for optional local live smoke tests only; it is not part of the required offline suite.
