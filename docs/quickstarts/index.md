---
title: Quickstarts
description: Provider and framework entry points for integrating AgentUQ without reading the full concepts or reference sections first.
slug: /quickstarts
sidebar_position: 5
---

# Quickstarts

Use these pages when you already know which provider or framework surface you want to wire.

## Direct provider surfaces

- [OpenAI](openai.md): default starting point for Responses or Chat Completions
- [OpenRouter](openrouter.md): OpenAI-compatible routing with parameter-preservation caveats
- [LiteLLM](litellm.md): gateway-oriented OpenAI-style integration
- [Gemini](gemini.md): `generate_content` and `logprobsResult`
- [Fireworks](fireworks.md): OpenAI-compatible chat completions with compatibility fallbacks
- [Together](together.md): chat completions with token arrays and top-logprob maps

## Framework and orchestration surfaces

- [LangChain](langchain.md): middleware-style wrapping for response metadata enrichment
- [LangGraph](langgraph.md): graph-state enrichment and interrupt-style gating
- [OpenAI Agents SDK](openai_agents.md): raw Responses extraction inside Agents workflows

## Picking the fastest route

- New provider-backed agent flow: start with [OpenAI](openai.md)
- Router or gateway flow: start with [OpenRouter](openrouter.md) or [LiteLLM](litellm.md)
- Existing framework integration: start with [LangChain](langchain.md) or [LangGraph](langgraph.md)

