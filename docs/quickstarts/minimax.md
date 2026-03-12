---
title: MiniMax Quickstart
description: Normalize MiniMax chat completions into AgentUQ records and capability reports.
slug: /quickstarts/minimax
sidebar_position: 7
---

# MiniMax Quickstart

MiniMax exposes an OpenAI-compatible chat completions endpoint at `https://api.minimax.io/v1` and supports `logprobs` and `top_logprobs` parameters in the standard OpenAI format.

**Status:** `Preview`

## Install

```bash
pip install agentuq openai
```

## Minimal request with readable terminal output

```python
from openai import OpenAI
from agentuq import Analyzer, UQConfig
from agentuq.adapters.minimax import MiniMaxAdapter

client = OpenAI(base_url="https://api.minimax.io/v1", api_key="...")
response = client.chat.completions.create(
    model="MiniMax-M2.5",
    messages=[{"role": "user", "content": "Return a SQL query for active users."}],
    logprobs=True,
    top_logprobs=5,
    temperature=0.01,
    top_p=1.0,
)

adapter = MiniMaxAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(
    response,
    {
        "model": "MiniMax-M2.5",
        "logprobs": True,
        "top_logprobs": 5,
        "temperature": 0.01,
        "top_p": 1.0,
    },
)
result = analyzer.analyze_step(
    record,
    adapter.capability_report(
        response,
        {
            "model": "MiniMax-M2.5",
            "logprobs": True,
            "top_logprobs": 5,
            "temperature": 0.01,
            "top_p": 1.0,
        },
    ),
)
print(result.pretty())
```

## Available models

- `MiniMax-M2.5`: flagship model with 204K context window
- `MiniMax-M2.5-highspeed`: optimized for lower latency

## Troubleshooting

- Request `logprobs=True` and `top_logprobs=k`.
- MiniMax requires `temperature` in the range `(0.0, 1.0]`. Use `0.01` instead of `0.0` for near-deterministic behavior.
- The response format matches OpenAI Chat Completions, so logprobs appear in `choices[0].logprobs.content`.
