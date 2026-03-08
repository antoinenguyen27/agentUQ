from dataclasses import dataclass, field

from uq_runtime.integrations.langchain_middleware import UQMiddleware


@dataclass
class DummyModel:
    def invoke(self, *_args, **_kwargs):
        return DummyResponse()


@dataclass
class DummyResponse:
    content: str = 'Action: weather_lookup {"city":"Pariss"}'
    response_metadata: dict = field(
        default_factory=lambda: {
            "logprobs": {
                "content": [
                    {"token": "weather_lookup", "logprob": -0.3, "top_logprobs": [{"token": "weather_lookup", "logprob": -0.3}, {"token": "search", "logprob": -0.8}]}
                ]
            }
        }
    )
    additional_kwargs: dict = field(default_factory=dict)


def main() -> None:
    model = UQMiddleware(DummyModel())
    response = model.invoke("weather")
    print(response.response_metadata["uq_result"]["action"])


if __name__ == "__main__":
    main()

