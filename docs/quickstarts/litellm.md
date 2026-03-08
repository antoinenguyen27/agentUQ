# LiteLLM Quickstart

LiteLLM is treated as a transport and compatibility layer, not as a separate scoring path.

## Install

```bash
pip install litellm
pip install -e .[dev]
```

## Minimal request

```python
from litellm import completion
from uq_runtime.adapters.litellm import LiteLLMAdapter
from uq_runtime.analysis.analyzer import Analyzer

response = completion(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Return JSON for Paris weather"}],
    logprobs=True,
    top_logprobs=5,
    drop_params=False,
    temperature=0.0,
)

adapter = LiteLLMAdapter()
request_meta = {
    "model": "openai/gpt-4o-mini",
    "logprobs": True,
    "top_logprobs": 5,
    "drop_params": False,
    "deterministic": True,
}
record = adapter.capture(response, request_meta)
result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
print(result.capability_report)
```

## Troubleshooting

- Prefer `drop_params=False` in UQ-critical paths.
- If you can collect `supported_openai_params`, pass them into `request_meta` so capability reporting is explicit.

## Sample output excerpt

```text
capability=selected_only
event=MISSING_TOPK
```
