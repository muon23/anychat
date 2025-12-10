"""
OpenAI DALL-E image generation implementation.
"""
import logging
import os
from typing import List

from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper

from t2i.ImageGenerator import ImageGenerator, ImageResponse


class DallEImageGenerator(ImageGenerator):
    """
    Concrete implementation for OpenAI's DALL-E image generation models.
    """
    
    __DEFAULT_TOKEN_LIMIT = 4096
    
    # Model metadata
    __MODELS = {
        "dall-e-3": {
            "aliases": ["dalle-3", "dalle3"],
            "size": "1024x1024",  # Default size
            "quality": "standard",  # "standard" or "hd"
            "style": "vivid",  # "vivid" or "natural"
        },
        "dall-e-2": {
            "aliases": ["dalle-2", "dalle2"],
            "size": "1024x1024",  # "256x256", "512x512", or "1024x1024"
        },
    }
    
    # List of all canonical model names
    SUPPORTED_MODELS = list(__MODELS.keys())
    
    MODEL_ALIASES = ImageGenerator._alias2model(__MODELS)
    
    def __init__(self, model_name: str = "dall-e-3", model_key: str = None, **kwargs):
        """
        Initializes the DALL-E image generator.
        
        Args:
            model_name: The DALL-E model to use ("dall-e-3" or "dall-e-2").
            model_key: The OpenAI API key. Searches environment variable if None.
            **kwargs: Additional parameters (size, quality, style for dall-e-3).
        
        Raises:
            ValueError: If the model is not supported.
            RuntimeError: If the API key is not found.
        """
        self.model_name = model_name
        
        # Check if it's an alias and convert to canonical name
        if self.model_name in self.MODEL_ALIASES:
            self.model_name = self.MODEL_ALIASES[self.model_name]
        
        if self.model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"DALL-E model {model_name} not supported. Supported: {self.SUPPORTED_MODELS}")
        
        logging.info(f"Using DALL-E model: {self.model_name}")
        
        # API Key management
        self.model_key = model_key if model_key else os.environ.get("OPENAI_API_KEY", None)
        if not self.model_key:
            raise RuntimeError("OpenAI API key not provided")
        
        # Initialize DALL-E wrapper
        # Note: DallEAPIWrapper uses OPENAI_API_KEY from environment or can be passed
        os.environ["OPENAI_API_KEY"] = self.model_key
        
        # Get model-specific defaults
        model_config = self.__MODELS[self.model_name].copy()
        # Override with kwargs if provided
        model_config.update(kwargs)
        
        self.size = model_config.get("size", "1024x1024")
        self.quality = model_config.get("quality", "standard") if self.model_name == "dall-e-3" else None
        self.style = model_config.get("style", "vivid") if self.model_name == "dall-e-3" else None
        
        # Initialize the wrapper
        # Note: DallEAPIWrapper may need to be configured for dall-e-3 vs dall-e-2
        self.wrapper = DallEAPIWrapper()
    
    def generate(self, prompt: str, **kwargs) -> ImageResponse:
        """
        Generates an image using DALL-E.
        
        Args:
            prompt: The text description of the image to generate.
            **kwargs: Additional parameters:
                     - size: Image size (e.g., "1024x1024", "512x512")
                     - quality: For dall-e-3 only ("standard" or "hd")
                     - style: For dall-e-3 only ("vivid" or "natural")
        
        Returns:
            ImageResponse with the generated image URL.
        """
        # Get parameters (use instance defaults, override with kwargs)
        size = kwargs.get("size", self.size)
        quality = kwargs.get("quality", self.quality) if self.model_name == "dall-e-3" else None
        style = kwargs.get("style", self.style) if self.model_name == "dall-e-3" else None
        
        try:
            # Call DALL-E API
            # Note: DallEAPIWrapper.run() returns a URL string
            # For dall-e-3, we may need to use the OpenAI client directly for more control
            response = None
            if self.model_name == "dall-e-3":
                # Use OpenAI client directly for dall-e-3 with more options
                from openai import OpenAI
                client = OpenAI(api_key=self.model_key)
                
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    style=style,
                    n=1,
                )
                
                image_url = response.data[0].url
                revised_prompt = response.data[0].revised_prompt if hasattr(response.data[0], 'revised_prompt') else None
            else:
                # Use LangChain wrapper for dall-e-2
                image_url = self.wrapper.run(prompt)
                revised_prompt = None
            
            return ImageResponse(
                image_url=image_url,
                revised_prompt=revised_prompt,
                raw=response,
            )
        except Exception as e:
            logging.error(f"Error generating image with DALL-E: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Returns the model name."""
        return self.model_name
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns list of supported models (including aliases)."""
        return list(cls.MODEL_ALIASES.keys()) + cls.SUPPORTED_MODELS

