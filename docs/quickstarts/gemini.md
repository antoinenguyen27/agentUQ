# Gemini Quickstart

Gemini exposes chosen-token and top-candidate logprobs through `responseLogprobs` and `logprobs`.

## Install

```bash
pip install google-genai
pip install -e .[dev]
```

## Minimal request

```python
from google import genai
from uq_runtime.adapters.gemini import GeminiAdapter
from uq_runtime.analysis.analyzer import Analyzer

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Return JSON for the weather in Paris",
    config={
        "responseLogprobs": True,
        "logprobs": 5,
        "temperature": 0.0,
    },
)

adapter = GeminiAdapter()
request_meta = {"model": "gemini-2.5-flash", "responseLogprobs": True, "logprobs": 5, "deterministic": True}
record = adapter.capture(response, request_meta)
result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
print(result.mode, result.action)
```

## Where the adapter reads data

AgentUQ reads `candidate.logprobsResult` and normalizes chosen candidates plus top candidates into the shared token format.

## Sample output excerpt

```text
mode=canonical
primary_score_type=g_nll
```

## Troubleshooting

- If `responseLogprobs` is absent, Gemini will not return chosen-token logprobs.
- If `logprobs` is omitted, AgentUQ will degrade to selected-only capability.
