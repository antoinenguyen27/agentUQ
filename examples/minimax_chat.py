from agentuq.adapters.minimax import MiniMaxAdapter
from agentuq.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "mm_1",
        "model": "MiniMax-M2.5",
        "choices": [
            {
                "message": {"content": "SELECT email FROM users WHERE active = true"},
                "logprobs": {
                    "content": [
                        {"token": "SELECT", "logprob": -0.1, "top_logprobs": [{"token": "SELECT", "logprob": -0.1}, {"token": "UPDATE", "logprob": -1.5}]},
                        {"token": " email", "logprob": -0.2, "top_logprobs": [{"token": " email", "logprob": -0.2}, {"token": " id", "logprob": -0.8}]},
                        {"token": " FROM", "logprob": -0.05, "top_logprobs": [{"token": " FROM", "logprob": -0.05}]},
                        {"token": " users", "logprob": -0.3, "top_logprobs": [{"token": " users", "logprob": -0.3}, {"token": " accounts", "logprob": -1.2}]},
                        {"token": " WHERE", "logprob": -0.1, "top_logprobs": [{"token": " WHERE", "logprob": -0.1}]},
                        {"token": " active", "logprob": -0.4, "top_logprobs": [{"token": " active", "logprob": -0.4}, {"token": " status", "logprob": -1.0}]},
                        {"token": " =", "logprob": -0.05, "top_logprobs": [{"token": " =", "logprob": -0.05}]},
                        {"token": " true", "logprob": -0.15, "top_logprobs": [{"token": " true", "logprob": -0.15}, {"token": " 1", "logprob": -0.9}]},
                    ],
                },
            }
        ],
    }
    request_meta = {"logprobs": True, "top_logprobs": 2, "temperature": 0.01, "top_p": 1.0}
    adapter = MiniMaxAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
