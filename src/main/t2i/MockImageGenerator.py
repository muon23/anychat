"""
Mock ImageGenerator for UI development and testing.

This generator returns a mock image (Cursor logo) without actually calling any image generation API.
Useful for UI development and testing without API costs.
"""
import logging
from typing import List

from t2i.ImageGenerator import ImageGenerator
from t2i.ImageResponse import ImageResponse


class MockImageGenerator(ImageGenerator):
    """
    Mock implementation that returns a placeholder image without calling any API.
    
    Returns the Cursor logo URL or a placeholder image for UI development.
    """

    # Model metadata
    __MODELS = {
        "mock": {
            "aliases": ["test", "placeholder", "mock-image"],
        },
    }

    # List of all canonical model names
    SUPPORTED_MODELS = list(__MODELS.keys())

    MODEL_ALIASES = ImageGenerator._alias2model(__MODELS)

    # Cursor logo URL (publicly available)
    CURSOR_LOGO_URL = "https://cursor.sh/favicon.ico"

    def __init__(self, model_name: str = "mock", **kwargs):
        """
        Initializes the Mock image generator.

        Args:
            model_name: The model to use (defaults to "mock").
            **kwargs: Additional parameters (ignored for mock).

        Raises:
            ValueError: If the model is not supported.
        """
        self.model_name = model_name

        # Check if it's an alias and convert to canonical name
        if self.model_name in self.MODEL_ALIASES:
            self.model_name = self.MODEL_ALIASES[self.model_name]

        if self.model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Mock model {model_name} not supported. Supported: {self.SUPPORTED_MODELS}")

        logging.info(f"Using Mock image generator: {self.model_name}")

    def generate(self, prompt: str, **kwargs) -> ImageResponse:
        """
        Generates a mock image (returns Cursor logo URL).

        Args:
            prompt: The text description (ignored for mock).
            **kwargs: Additional parameters (ignored for mock).

        Returns:
            ImageResponse with the Cursor logo URL.
        """
        logging.debug(f"MockImageGenerator.generate() called with prompt: {prompt}")
        
        # Return the Cursor logo URL
        # You can switch to PLACEHOLDER_URL if the Cursor logo URL doesn't work
        return ImageResponse(
            image_type="url",
            image=self.CURSOR_LOGO_URL,
            revised_prompt=f"[Mock] {prompt}",
            raw={"mock": True, "prompt": prompt}
        )

    def get_model_name(self) -> str:
        """Returns the model name."""
        return self.model_name

    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns list of supported models (including aliases)."""
        return list(cls.MODEL_ALIASES.keys()) + cls.SUPPORTED_MODELS

