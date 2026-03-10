from agentuq.adapters.gemini import GeminiAdapter
from agentuq.adapters.openai_chat import OpenAIChatAdapter
from agentuq.adapters.openai_responses import OpenAIResponsesAdapter
from agentuq.adapters.together import TogetherAdapter


def test_openai_chat_adapter_normalizes_tool_calls():
    response = {
        "id": "chatcmpl_1",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "content": "Checking.",
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "weather", "arguments": '{"city":"Paris"}'}}
                    ],
                },
                "logprobs": {
                    "content": [
                        {"token": "Checking", "logprob": -0.1, "top_logprobs": [{"token": "Checking", "logprob": -0.1}, {"token": "Looking", "logprob": -0.9}]},
                        {"token": ".", "logprob": -0.2, "top_logprobs": [{"token": ".", "logprob": -0.2}, {"token": "!", "logprob": -0.8}]},
                    ]
                },
            }
        ],
    }
    record = OpenAIChatAdapter().capture(response, {"logprobs": True, "top_logprobs": 2})
    assert any(block.type == "tool_call" for block in record.structured_blocks)
    assert record.structured_blocks[-1].metadata["token_grounded"] is False
    assert record.selected_tokens == ["Checking", "."]


def test_openai_responses_adapter_collects_output_text_logprobs():
    response = {
        "id": "resp_1",
        "model": "gpt-4.1-mini",
        "output": [
            {"type": "function_call", "name": "weather_lookup", "arguments": '{"city":"Paris"}'},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Hello",
                        "logprobs": [{"token": "Hello", "logprob": -0.2, "top_logprobs": [{"token": "Hello", "logprob": -0.2}]}],
                    }
                ],
            }
        ],
    }
    record = OpenAIResponsesAdapter().capture(response, {"include": ["message.output_text.logprobs"], "top_logprobs": 1})
    assert record.selected_logprobs == [-0.2]
    assert record.structured_blocks[0].metadata["token_grounded"] is False


def test_gemini_adapter_reads_logprobs_result():
    response = {
        "responseId": "g_1",
        "modelVersion": "gemini-2.5-flash",
        "candidates": [
            {
                "content": {"parts": [{"text": "Paris"}]},
                "logprobsResult": {
                    "chosenCandidates": [{"token": "Paris", "logProbability": -0.2}],
                    "topCandidates": [{"candidates": [{"token": "Paris", "logProbability": -0.2}, {"token": "London", "logProbability": -0.9}]}],
                },
            }
        ],
    }
    record = GeminiAdapter().capture(response, {"responseLogprobs": True, "logprobs": 2})
    assert record.selected_tokens == ["Paris"]
    assert record.top_logprobs and record.top_logprobs[0][1].token == "London"


def test_together_adapter_maps_top_logprobs():
    response = {
        "id": "t_1",
        "model": "meta-llama/test",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Paris"},
                "logprobs": {
                    "tokens": ["Paris"],
                    "token_logprobs": [-0.3],
                    "top_logprobs": [{"Paris": -0.3, "London": -0.8}],
                },
            }
        ],
    }
    record = TogetherAdapter().capture(response, {"logprobs": 2})
    assert record.top_logprobs and record.top_logprobs[0][0].token == "Paris"
