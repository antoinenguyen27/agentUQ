# Gemini Quickstart

Gemini exposes chosen-token and top-candidate logprobs through `responseLogprobs` and `logprobs`.

## Install

```bash
pip install google-genai
pip install -e .[dev]
```

## Minimal request with readable terminal output

```python
from google import genai
from uq_runtime.adapters.gemini import GeminiAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = genai.Client()
request_meta = {
    "model": "gemini-2.5-flash",
    "responseLogprobs": True,
    "logprobs": 5,
    "temperature": 0.0,
    "topP": 1.0,
    "deterministic": True,
}
response = client.models.generate_content(
    model=request_meta["model"],
    contents="Return JSON for the weather in Paris.",
    config={
        "responseLogprobs": request_meta["responseLogprobs"],
        "logprobs": request_meta["logprobs"],
        "temperature": request_meta["temperature"],
        "topP": request_meta["topP"],
    },
)

adapter = GeminiAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="balanced"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Where the adapter reads data

AgentUQ reads `candidate.logprobsResult` and normalizes chosen candidates plus top candidates into the shared token format.

## Sample output excerpt

```text
Summary
  recommended_action: Continue
  rationale: Policy preset balanced selected continue based on segment events.
  mode: canonical
  whole_response_score: 1.116 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  JSON value [important_action] -> Continue
    text: sunny
    surprise: score=0.387 nll=0.387 avg=0.194 p95=0.271 max=0.271 tail=0.271
    events: none
```

## Troubleshooting

- If `responseLogprobs` is absent, Gemini will not return chosen-token logprobs.
- If `logprobs` is omitted, AgentUQ will degrade to selected-only capability.
- Use this example for optional local drift/smoke checks, not required CI.
