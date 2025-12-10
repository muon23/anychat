"""
Text-to-Image (T2I) Package Factory (__init__.py)

This module serves as the primary factory for creating ImageGenerator instances.
It transparently selects the correct concrete ImageGenerator subclass (e.g., DallEImageGenerator, DeepInfraImageGenerator)
based on the requested model name.
"""
from t2i.DallEImageGenerator import DallEImageGenerator
from t2i.DeepInfraImageGenerator import DeepInfraImageGenerator
from t2i.ReplicateImageGenerator import ReplicateImageGenerator
from t2i.GeminiImageGenerator import GeminiImageGenerator
from t2i.MockImageGenerator import MockImageGenerator
from t2i.ImageGenerator import ImageGenerator


def of(model_name: str, **kwargs) -> ImageGenerator:
    """
    Factory function to instantiate the correct ImageGenerator subclass based on the model name.

    The function iterates through all known ImageGenerator subclasses and checks if the
    requested model_name is supported by that class.

    Args:
        model_name: The name of the image generation model requested (e.g., 'dall-e-3', 'black-forest-labs/FLUX-pro').
        **kwargs: Arbitrary keyword arguments passed directly to the constructor
                  of the selected ImageGenerator subclass (e.g., API keys, size, quality, style).

    Returns:
        An instantiated object of the correct ImageGenerator subclass.

    Raises:
        RuntimeError: If the provided model_name is not supported by any known subclass.
    """
    generators = [DallEImageGenerator, DeepInfraImageGenerator, ReplicateImageGenerator, GeminiImageGenerator, MockImageGenerator]

    for generator in generators:
        # Check if the model_name is in the list of supported models for this class
        if model_name in generator.get_supported_models():
            # Found the correct provider, instantiate and return
            return generator(model_name, **kwargs)

    # If the loop completes without finding a match
    raise RuntimeError(f"Model {model_name} not supported.")

