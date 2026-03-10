from agentuq.adapters.fireworks import FireworksAdapter
from agentuq.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "fw_1",
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "choices": [
            {
                "message": {"content": "SELECT email"},
                "logprobs": {
                    "tokens": ["SELECT", " email"],
                    "token_logprobs": [-0.2, -0.1],
                    "top_logprobs": [
                        [{"token": "SELECT", "logprob": -0.2}, {"token": "UPDATE", "logprob": -1.0}],
                        [{"token": " email", "logprob": -0.1}, {"token": " id", "logprob": -0.5}],
                    ],
                },
            }
        ],
    }
    request_meta = {"logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0}
    adapter = FireworksAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
