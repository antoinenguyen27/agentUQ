from uq_runtime.adapters.gemini import GeminiAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "responseId": "gem_1",
        "modelVersion": "gemini-2.5-flash",
        "candidates": [
            {
                "content": {"parts": [{"text": 'navigate(url="https://example.com/delete")'}]},
                "logprobsResult": {
                    "chosenCandidates": [{"token": "navigate", "logProbability": -0.7}],
                    "topCandidates": [{"candidates": [{"token": "navigate", "logProbability": -0.7}, {"token": "click", "logProbability": -0.8}]}],
                },
            }
        ],
    }
    request_meta = {"responseLogprobs": True, "logprobs": 2, "temperature": 0.7, "deterministic": False}
    adapter = GeminiAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
