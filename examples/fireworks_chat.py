from uq_runtime.adapters.fireworks import FireworksAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "fw_1",
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "choices": [{"message": {"content": "SELECT * FROM users WHERE email = 'a@example.com'"}, "logprobs": {"content": [{"token": "SELECT", "logprob": -0.2, "top_logprobs": [{"token": "SELECT", "logprob": -0.2}, {"token": "UPDATE", "logprob": -1.0}]}]}}],
    }
    request_meta = {"logprobs": True, "top_logprobs": 2, "deterministic": True}
    adapter = FireworksAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.action)


if __name__ == "__main__":
    main()

