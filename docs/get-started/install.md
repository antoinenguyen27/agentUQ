---
title: Install
description: Install AgentUQ from PyPI, then layer on optional extras or the editable contributor workflow when needed.
slug: /get-started/install
sidebar_position: 3
---

# Install

AgentUQ is a Python package. The docs site is separate and lives in `website/`, but the library install flow is still the core first step for contributors and evaluators.

## Install from PyPI

```bash
pip install agentuq
```

## Local editable install

Use the editable install when you are contributing to the library itself:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Examples in the docs assume the public import namespace `agentuq`.

## Optional Rich rendering

Install the optional Rich extra when you want terminal-native rendering helpers:

```bash
pip install 'agentuq[rich]'
```

## Provider SDKs

AgentUQ normalizes upstream payloads, so provider SDKs are installed separately depending on the quickstart you use.

OpenAI Responses API is the stable integration path. The other provider, gateway, and framework quickstarts are preview.

- OpenAI / OpenRouter: `pip install openai`
- Gemini: `pip install google-genai`
- Fireworks: `pip install openai`
- Together: `pip install together`
- LiteLLM: `pip install litellm`
- LangChain / LangGraph / OpenAI Agents: install the relevant framework packages alongside AgentUQ

See the [Quickstarts](../quickstarts/index.md) section for exact examples.

## Next steps

- Read the [Quickstart](quickstart.md) for the minimal runtime loop.
- Go directly to [OpenAI Quickstart](../quickstarts/openai.md) if you want the default provider-first path.
- Read [Testing](../concepts/testing.md) if you are contributing rather than only evaluating.
