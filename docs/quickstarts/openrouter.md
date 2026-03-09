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
from uq_runtime.schemas.config import UQConfig

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key="...")
response = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "Return the single word Paris."}],
    logprobs=True,
    top_logprobs=5,
    provider={"require_parameters": True},
    temperature=0.0,
)

adapter = OpenRouterAdapter()
analyzer = Analyzer(UQConfig(policy="conservative", tolerance="strict"))
request_meta = {
    "model": "openai/gpt-4o-mini",
    "logprobs": True,
    "top_logprobs": 5,
    "provider": {"require_parameters": True},
    "temperature": 0.0,
    "top_p": 1.0,
}
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.decision.action)
```

## Notes

- `provider.require_parameters=true` prevents silent routing to a backend that ignores logprob settings.
- If runtime capability still degrades, inspect the routed provider metadata and the returned `CapabilityReport`.

## Sample output excerpt

```text
capability=full
segment=final_answer_text action=continue
```

## Troubleshooting

- If `CapabilityReport.selected_token_logprobs` is false, the routed backend likely ignored logprob settings.
- Keep fail-loud behavior on for action-critical runs.
- OpenRouter inherits the upstream OpenAI-compatible chat logprob surface; structural `tool_calls` do not imply token-grounded tool uncertainty.
- This example is suitable for local live smoke testing, but not for required public CI.
