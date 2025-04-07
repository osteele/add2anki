"""Translation service using OpenAI's API."""

import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from add2anki.exceptions import ConfigurationError, TranslationError

# Define the style types
StyleType = Literal["written", "formal", "conversational"]


class TranslationResult(BaseModel):
    """Model for translation results."""

    hanzi: str = Field(description="The Chinese characters (Hanzi)")
    pinyin: str = Field(description="The romanization of the Chinese characters (Pinyin)")
    english: str = Field(description="The original English text")
    style: StyleType = Field(description="The style of the translation")


class TranslationService:
    """Service for translating text using OpenAI's API."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o") -> None:
        """Initialize the translation service.

        Args:
            api_key: OpenAI API key. If None, will try to get from environment.
            model: The OpenAI model to use for translation.

        Raises:
            ConfigurationError: If the API key is not provided and not in environment.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ConfigurationError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def translate(self, text: str, style: StyleType = "conversational") -> TranslationResult:
        """Translate English text to Mandarin Chinese with Pinyin.

        Args:
            text: The English text to translate.
            style: The style of the translation. Options are:
                - "written": More formal, suitable for written text
                - "formal": Polite and respectful, suitable for formal situations
                - "conversational": Casual and natural, suitable for everyday conversation (default)

        Returns:
            A TranslationResult object containing the translation.

        Raises:
            TranslationError: If there is an error with the translation service.
        """
        # Create style-specific instructions
        style_instructions = {
            "written": "Use a more formal, literary style suitable for written text. "
            "Prefer more sophisticated vocabulary and sentence structures.",
            "formal": "Use polite and respectful language suitable for formal situations. "
            "Include appropriate honorifics and formal expressions.",
            "conversational": "Use casual, natural language as would be used in everyday conversation. "
            "Use common expressions and colloquial terms where appropriate.",
        }

        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful assistant that translates English to Mandarin Chinese. "
                    f"Provide the translation in both Chinese characters (Hanzi) and Pinyin. "
                    f"{style_instructions[style]} "
                    f"Respond with a JSON object with the fields 'hanzi', 'pinyin', and 'english'.",
                },
                {
                    "role": "user",
                    "content": f"Translate the following English text to Mandarin Chinese: {text}",
                },
            ],
        )

        # Parse the response content as JSON
        content = response.choices[0].message.content
        if not content:
            raise TranslationError("Empty response from OpenAI API")

        # Use Pydantic to validate the response
        import json

        try:
            data = json.loads(content)
            return TranslationResult(
                hanzi=data.get("hanzi", ""),
                pinyin=data.get("pinyin", ""),
                english=data.get("english", text),
                style=style,
            )
        except json.JSONDecodeError as e:
            raise TranslationError(f"Failed to parse OpenAI response as JSON: {e}") from e
