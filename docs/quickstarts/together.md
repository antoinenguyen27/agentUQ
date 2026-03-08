# Together Quickstart

Together returns token lists, token logprobs, and top-logprob maps in its response payload.

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

client = Together(api_key="...")
response = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    messages=[{"role": "user", "content": "Return a browser command to click submit"}],
    logprobs=5,
    temperature=0.0,
)

adapter = TogetherAdapter()
request_meta = {"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "logprobs": 5, "deterministic": True}
record = adapter.capture(response, request_meta)
result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
print(result.events)
```

## Sample output excerpt

```text
event=ARGUMENT_VALUE_UNCERTAIN
action=ask_user_confirmation
```

## Troubleshooting

- Together uses `logprobs=k` rather than separate `top_logprobs`.
- Verify that the response includes `tokens`, `token_logprobs`, and `top_logprobs`.
