from typing import Any, Callable, Dict, Optional

from guardrails.validator_base import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

try:
    from transformers import pipeline
except ImportError:
    pipeline = None

try:
    import nltk  # type: ignore
except ImportError:
    nltk = None  # type: ignore

if nltk is not None:
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt")


@register_validator(name="cartesia/financial-tone", data_type="string")
class FinancialTone(Validator):
    """Validates that the generated text has a certain financial tone.

    **Key Properties**

    | Property                     | Description                   |
    |------------------------------|-------------------------------|
    | Name for `format` attribute  | `cartesia/financial-tone`     |
    | Supported data types         | `string`                      |
    | Programmatic fix             | N/A                           |

    This validator uses the pre-trained model from HuggingFace -
    `yiyanghkust/finbert-tone` to check whether the generated text has the right
    financial tone.
    """

    DEFAULT_THRESHOLD = 0.8
    DEFAULT_TONE = "neutral"

    def __init__(self, on_fail: Optional[Callable] = None, **kwargs):
        super().__init__(on_fail, **kwargs)

        # Check if transformers.pipeline is imported
        if pipeline is None:
            raise ValueError(
                "You must install transformers in order to "
                "use the FinancialTone validator."
                "Install it using `pip install transformers`."
            )

        # Define the model, pipeline and labels
        self._pipe = pipeline("text-classification", model="yiyanghkust/finbert-tone")
        print("Pipeline setup successfully.")

    def has_correct_financial_tone(
        self, value: str, financial_tone: str, threshold: float
    ) -> bool:
        """Determines if the generated text is NSFW.

        Args:
            value (str): The generated text.

        Returns:
            bool: Whether the generated text is NSFW.
        """
        result = self._pipe(value)
        if not result:
            raise RuntimeError("Failed to get model prediction.")

        pred_label, confidence = result[0]["label"], result[0]["score"]  # type: ignore
        assert pred_label in ["Positive", "Negative", "Neutral"]

        print(f"Predicted label: {pred_label}, Confidence: {confidence}")

        if pred_label.lower() == financial_tone and confidence > threshold:
            return True
        return False

    def _unpack_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Unpacks the metadata and returns the relevant fields."""
        financial_tone = metadata.get("financial_tone", self.DEFAULT_TONE)
        assert financial_tone in [
            "positive",
            "negative",
            "neutral",
        ], "The key `financial_tone` must be one of 'positive', 'negative', 'neutral."
        return financial_tone, float(
            metadata.get("financial_tone_threshold", self.DEFAULT_THRESHOLD)
        )

    def validate(self, value: str, metadata: Dict[str, Any]) -> ValidationResult:
        """Validate that the generated text has a certain financial tone."""
        financial_tone, threshold = self._unpack_metadata(metadata)
        if not self.has_correct_financial_tone(value, financial_tone, threshold):
            return FailResult(
                metadata=metadata,
                error_message=f"The generated text didn't have tone {financial_tone}.",
            )
        return PassResult()


if __name__ == "__main__":
    validator = FinancialTone()
    print(validator.validate("I'm okay.", {}))
    print(
        validator.validate(
            "This is an interesting increase.", {"financial_tone": "positive"}
        )
    )
    print(
        validator.validate(
            "This is an exciting opportunity.", {"financial_tone": "positive"}
        )
    )
    breakpoint()
