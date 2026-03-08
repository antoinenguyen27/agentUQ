# OpenRouter Quickstart

For UQ-critical runs, require the router to preserve requested parameters.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request

```python
from openai import OpenAI
from uq_runtime.adapters.openrouter import OpenRouterAdapter
from uq_runtime.analysis.analyzer import Analyzer

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key="...")
response = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Call the weather tool for Paris"}],
    logprobs=True,
    top_logprobs=5,
    provider={"require_parameters": True},
    temperature=0.0,
)

adapter = OpenRouterAdapter()
request_meta = {
    "model": "openai/gpt-4o-mini",
    "logprobs": True,
    "top_logprobs": 5,
    "provider": {"require_parameters": True},
    "deterministic": True,
}
record = adapter.capture(response, request_meta)
result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
print(result.decision.action)
```

## Notes

- `provider.require_parameters=true` prevents silent routing to a backend that ignores logprob settings.
- If runtime capability still degrades, inspect the routed provider metadata and the returned `CapabilityReport`.

## Sample output excerpt

```text
capability=full
segment=tool_name action=retry_step_with_constraints
```

## Troubleshooting

- If `CapabilityReport.selected_token_logprobs` is false, the routed backend likely ignored logprob settings.
- Keep fail-loud behavior on for action-critical runs.
