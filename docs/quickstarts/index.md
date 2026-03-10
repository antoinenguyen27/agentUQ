---
title: Quickstarts
description: Provider and framework entry points for integrating AgentUQ without reading the full concepts or reference sections first.
slug: /quickstarts
sidebar_position: 5
---

# Quickstarts

Use these pages when you already know which provider or framework surface you want to wire.

**Status policy:** OpenAI Responses API is the only stable integration in the current docs set. Every other provider, gateway, and framework surface is preview.

## Direct provider surfaces

- [OpenAI](openai.md): OpenAI Responses API (`Stable`) and Chat Completions (`Preview`)
- [OpenRouter](openrouter.md): OpenAI-compatible routing with parameter-preservation caveats (`Preview`)
- [LiteLLM](litellm.md): gateway-oriented OpenAI-style integration (`Preview`)
- [Gemini](gemini.md): `generate_content` and `logprobsResult` (`Preview`)
- [Fireworks](fireworks.md): OpenAI-compatible chat completions with compatibility fallbacks (`Preview`)
- [Together](together.md): chat completions with token arrays and top-logprob maps (`Preview`)

## Framework and orchestration surfaces

- [LangChain](langchain.md): middleware-style wrapping for response metadata enrichment (`Preview`)
- [LangGraph](langgraph.md): graph-state enrichment and interrupt-style gating (`Preview`)
- [OpenAI Agents SDK](openai_agents.md): raw Responses extraction inside Agents workflows (`Preview`)

## Picking the fastest route

- New provider-backed agent flow: start with [OpenAI](openai.md) on the Responses API path
- Router or gateway flow: start with [OpenRouter](openrouter.md) or [LiteLLM](litellm.md)
- Existing framework integration: start with [LangChain](langchain.md) or [LangGraph](langgraph.md)
