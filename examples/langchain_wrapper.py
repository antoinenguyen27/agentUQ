from dataclasses import dataclass, field

from uq_runtime.integrations.langchain_middleware import UQMiddleware


@dataclass
class DummyModel:
    def invoke(self, *_args, **_kwargs):
        return DummyResponse()


@dataclass
class DummyResponse:
    content: str = "Paris"
    response_metadata: dict = field(
        default_factory=lambda: {
            "logprobs": {
                "content": [
                    {"token": "Paris", "logprob": -0.3, "top_logprobs": [{"token": "Paris", "logprob": -0.3}, {"token": "London", "logprob": -0.8}]}
                ]
            }
        }
    )
    additional_kwargs: dict = field(default_factory=dict)


def main() -> None:
    model = UQMiddleware(DummyModel())
    response = model.invoke("city")
    print(response.response_metadata["uq_result"]["action"])


if __name__ == "__main__":
    main()
