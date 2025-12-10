"""
Abstract base class for image generation models.
"""
from abc import ABC, abstractmethod
from typing import List, Dict

from t2i.ImageResponse import ImageResponse


class ImageGenerator(ABC):
    """
    Abstract class for accessing image generation models.

    This class provides a standardized interface for interacting with different image
    generation providers (like DALL-E, Stable Diffusion, etc.). Concrete subclasses
    must implement provider-specific logic.
    """
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> ImageResponse:
        """
        Generates an image based on the given prompt.
        
        Args:
            prompt: The text description of the image to generate.
            **kwargs: Additional parameters (size, quality, style, etc.)
        
        Returns:
            ImageResponse with the generated image URL and metadata.
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Returns the canonical model name.
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_supported_models(cls) -> List[str]:
        """
        Returns a list of model names supported by the subclass.
        """
        pass
    
    @staticmethod
    def _alias2model(models: Dict[str, dict]) -> Dict[str, str]:
        """Helper to create a mapping from model aliases to canonical model names."""
        a2m = dict()
        for model, properties in models.items():
            aliases = properties.get("aliases", [])
            for alias in aliases:
                a2m[alias] = model
        return a2m

