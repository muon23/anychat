"""
Replicate image generation implementation.
Supports Replicate's text-to-image models.
"""
import base64
import logging
import os
from typing import List

import replicate

from t2i.ImageGenerator import ImageGenerator, ImageResponse


class ReplicateImageGenerator(ImageGenerator):
    """
    Concrete implementation for Replicate's image generation models.
    """
    
    # Model metadata
    __MODELS = {
        "prunaai/z-image-turbo": {
            "aliases": ["z-image"],
        },
    }
    
    # List of all canonical model names
    SUPPORTED_MODELS = list(__MODELS.keys())
    
    MODEL_ALIASES = ImageGenerator._alias2model(__MODELS)
    
    def __init__(self, model_name: str = "z-image-turbo", model_key: str = None, **kwargs):
        """
        Initializes the Replicate image generator.
        
        Args:
            model_name: The Replicate model to use (e.g., "z-image-turbo").
            model_key: The Replicate API token. Searches environment variable if None.
            **kwargs: Additional parameters (currently unused, but kept for consistency).
        
        Raises:
            ValueError: If the model is not supported.
            RuntimeError: If the API key is not found.
        """
        self.model_name = model_name
        
        # Check if it's an alias and convert to canonical name
        if self.model_name in self.MODEL_ALIASES:
            self.model_name = self.MODEL_ALIASES[self.model_name]
        
        if self.model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Replicate model {model_name} not supported. Supported: {self.SUPPORTED_MODELS}")
        
        logging.info(f"Using Replicate model: {self.model_name}")
        
        # API Key management
        self.model_key = model_key if model_key else os.environ.get("REPLICATE_API_TOKEN", None)
        if not self.model_key:
            raise RuntimeError("Replicate API token not provided")
        
        # Set the API token for the replicate client
        os.environ["REPLICATE_API_TOKEN"] = self.model_key
    
    def generate(self, prompt: str, **kwargs) -> ImageResponse:
        """
        Generates an image using Replicate.
        
        Args:
            prompt: The text description of the image to generate.
            **kwargs: Additional parameters (model-specific, passed to replicate.run).
        
        Returns:
            ImageResponse with the generated image URL.
        """
        try:
            # Call Replicate API
            # Replicate.run() returns an iterator that yields chunks of data
            output = replicate.run(
                self.model_name,
                input={"prompt": prompt, **kwargs}
            )
            
            image_url = None
            image_base64 = None
            
            # Replicate returns an iterator that yields chunks
            # We need to collect all chunks to get the complete image
            chunks = []
            for chunk in output:
                chunks.append(chunk)
            
            if not chunks:
                raise ValueError("No data in Replicate response")
            
            # Check the type of the first chunk to determine how to handle it
            first_chunk = chunks[0]
            
            if isinstance(first_chunk, bytes):
                # Binary image data - combine all chunks and convert to base64
                image_data = b''.join(chunks)
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            elif isinstance(first_chunk, str):
                # URL string - take the first one (or combine if multiple)
                if len(chunks) == 1:
                    url = chunks[0]
                else:
                    # Multiple URLs, take the first
                    url = chunks[0]
                
                if url.startswith(('http://', 'https://')):
                    image_url = url
                else:
                    # Might be a file path or other string, treat as URL
                    image_url = url
            else:
                # Unexpected type
                raise ValueError(f"Unexpected data type from Replicate: {type(first_chunk)}")
            
            if not image_url and not image_base64:
                raise ValueError("No image data (URL or binary) in Replicate response")
            
            return ImageResponse(
                image_url=image_url,
                image_base64=image_base64,
                revised_prompt=None,  # Replicate doesn't provide revised prompts
                raw=chunks,  # Store all chunks as raw data
            )
        except Exception as e:
            logging.error(f"Error generating image with Replicate: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Returns the model name."""
        return self.model_name
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns list of supported models (including aliases)."""
        return list(cls.MODEL_ALIASES.keys()) + cls.SUPPORTED_MODELS

