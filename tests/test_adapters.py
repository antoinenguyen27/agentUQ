from uq_runtime.adapters.gemini import GeminiAdapter
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.adapters.together import TogetherAdapter


def test_openai_chat_adapter_normalizes_tool_calls():
    response = {
        "id": "chatcmpl_1",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "weather", "arguments": '{"city":"Paris"}'}}
                    ],
                },
                "logprobs": {
                    "content": [
                        {"token": "weather", "logprob": -0.1, "top_logprobs": [{"token": "weather", "logprob": -0.1}, {"token": "search", "logprob": -0.9}]}
                    ]
                },
            }
        ],
    }
    record = OpenAIChatAdapter().capture(response, {"logprobs": True, "top_logprobs": 2})
    assert record.structured_blocks[0].type == "tool_call"
    assert record.selected_tokens == ["weather"]


def test_openai_responses_adapter_collects_output_text_logprobs():
    response = {
        "id": "resp_1",
        "model": "gpt-4.1-mini",
        "output": [
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
    record = OpenAIResponsesAdapter().capture(response, {"include_output_text_logprobs": True, "top_logprobs": 1})
    assert record.selected_logprobs == [-0.2]


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
        "output": {
            "text": "Paris",
            "tokens": ["Paris"],
            "token_logprobs": [-0.3],
            "top_logprobs": [{"Paris": -0.3, "London": -0.8}],
        },
    }
    record = TogetherAdapter().capture(response, {"logprobs": 2})
    assert record.top_logprobs and record.top_logprobs[0][0].token == "Paris"

