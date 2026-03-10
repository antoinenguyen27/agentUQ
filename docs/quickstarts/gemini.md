---
title: Gemini Quickstart
description: Use AgentUQ with Gemini generate_content responses and responseLogprobs surfaces.
slug: /quickstarts/gemini
sidebar_position: 5
---

# Gemini Quickstart

Gemini exposes chosen-token and top-candidate logprobs through `responseLogprobs` and `logprobs`.

**Status:** `Preview`

## Install

```bash
pip install agentuq google-genai
```

## Minimal request with readable terminal output

```python
from google import genai
from agentuq import Analyzer, UQConfig
from agentuq.adapters.gemini import GeminiAdapter

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Return JSON for the weather in Paris.",
    config={
        "responseLogprobs": True,
        "logprobs": 5,
        "temperature": 0.0,
        "topP": 1.0,
    },
)

adapter = GeminiAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="balanced"))
record = adapter.capture(
    response,
    {
        "model": "gemini-2.5-flash",
        "responseLogprobs": True,
        "logprobs": 5,
        "temperature": 0.0,
        "topP": 1.0,
    },
)
result = analyzer.analyze_step(
    record,
    adapter.capability_report(
        response,
        {
            "model": "gemini-2.5-flash",
            "responseLogprobs": True,
            "logprobs": 5,
            "temperature": 0.0,
            "topP": 1.0,
        },
    ),
)
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
