# Together Quickstart

Together chat completions return token lists, token logprobs, and top-logprob maps under `choices[0].logprobs`.

## Install

```bash
pip install together
pip install -e .[dev]
```

## Minimal request

```python
from together import Together
from uq_runtime.adapters.together import TogetherAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = Together(api_key="...")
response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    messages=[{"role": "user", "content": "Return a browser command to click submit"}],
    logprobs=5,
    temperature=0.0,
)

adapter = TogetherAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
request_meta = {"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "logprobs": 5, "deterministic": True}
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.events)
```

## Sample output excerpt

```text
event=ARGUMENT_VALUE_UNCERTAIN
action=ask_user_confirmation
```

## Troubleshooting

- Together uses `logprobs=k` rather than separate `top_logprobs`.
- Verify that `choices[0].logprobs` includes `tokens`, `token_logprobs`, and `top_logprobs`.
- Together-backed smoke checks should be run locally with your own API key, not in required CI.
