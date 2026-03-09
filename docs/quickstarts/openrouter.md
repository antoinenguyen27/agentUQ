# OpenRouter Quickstart

For UQ-critical runs, require the router to preserve requested parameters.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from openai import OpenAI
from uq_runtime.adapters.openrouter import OpenRouterAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key="...")
request_meta = {
    "model": "openai/gpt-4o-mini",
    "logprobs": True,
    "top_logprobs": 5,
    "provider": {"require_parameters": True},
    "temperature": 0.0,
    "top_p": 1.0,
}
response = client.chat.completions.create(
    model=request_meta["model"],
    messages=[{"role": "user", "content": "Return the single word Paris."}],
    logprobs=request_meta["logprobs"],
    top_logprobs=request_meta["top_logprobs"],
    provider=request_meta["provider"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = OpenRouterAdapter()
analyzer = Analyzer(UQConfig(policy="conservative", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Notes

- `provider.require_parameters=true` prevents silent routing to a backend that ignores logprob settings.
- If runtime capability still degrades, inspect the routed provider metadata and the returned `CapabilityReport`.

## Sample output excerpt

```text
Summary
  mode: canonical
  reason: auto-selected canonical mode from strictly greedy metadata
  score: 0.028 g_nll
  action: continue
  rationale: Policy preset conservative selected continue based on segment events.
  capability: full

Segments
  final_answer_text [informational] -> continue
    text: Paris.
    metrics: score=0.028 avg_surprise=0.014 max_surprise=0.021 mean_entropy=0.118
    events: none
```

## Troubleshooting

- If `CapabilityReport.selected_token_logprobs` is false, the routed backend likely ignored logprob settings.
- Keep fail-loud behavior on for action-critical runs.
- OpenRouter inherits the upstream OpenAI-compatible chat logprob surface; structural `tool_calls` do not imply token-grounded tool uncertainty.
- This example is suitable for local live smoke testing, but not for required public CI.
