"""
DeepInfra image generation implementation.
Supports FLUX and other DeepInfra text-to-image models.
"""
import logging
import os
from typing import List

import httpx

from t2i.ImageGenerator import ImageGenerator, ImageResponse


class DeepInfraImageGenerator(ImageGenerator):
    """
    Concrete implementation for DeepInfra's image generation models.
    """
    
    # Model metadata
    __MODELS = {
        "black-forest-labs/FLUX-2-pro": {
            "aliases": ["flux-2"],
            "size": "1024x1024",  # Default size
        },
        ## Unknown internal error from the server
        # "black-forest-labs/FLUX-pro": {
        #     "aliases": ["flux-pro", "fluxpro"],
        #     "size": "1024x1024",  # Default size
        # },
        "ByteDance/Seedream-4": {
            "aliases": ["seedream-4"],
            "size": "1024x1024",  # Default size
        },
        "stability-ai/stable-diffusion-3.5-large": {
            "aliases": ["sd-3.5"],
            "size": "1024x1024",
        },
    }
    
    # List of all canonical model names
    SUPPORTED_MODELS = list(__MODELS.keys())
    
    MODEL_ALIASES = ImageGenerator._alias2model(__MODELS)
    
    __API_URL = "https://api.deepinfra.com/v1/openai/images/generations"
    
    def __init__(self, model_name: str = "flux-2-pro", model_key: str = None, **kwargs):
        """
        Initializes the DeepInfra image generator.
        
        Args:
            model_name: The DeepInfra model to use (e.g., "black-forest-labs/FLUX-pro").
            model_key: The DeepInfra API key. Searches environment variable if None.
            **kwargs: Additional parameters (size, etc.).
        
        Raises:
            ValueError: If the model is not supported.
            RuntimeError: If the API key is not found.
        """
        self.model_name = model_name
        
        # Check if it's an alias and convert to canonical name
        if self.model_name in self.MODEL_ALIASES:
            self.model_name = self.MODEL_ALIASES[self.model_name]
        
        if self.model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"DeepInfra model {model_name} not supported. Supported: {self.SUPPORTED_MODELS}")
        
        logging.info(f"Using DeepInfra model: {self.model_name}")
        
        # API Key management
        self.model_key = model_key if model_key else os.environ.get("DEEPINFRA_API_KEY", None)
        if not self.model_key:
            raise RuntimeError("DeepInfra API key not provided")
        
        # Get model-specific defaults
        model_config = self.__MODELS[self.model_name].copy()
        # Override with kwargs if provided
        model_config.update(kwargs)
        
        self.size = model_config.get("size", "1024x1024")
    
    def generate(self, prompt: str, **kwargs) -> ImageResponse:
        """
        Generates an image using DeepInfra.
        
        Args:
            prompt: The text description of the image to generate.
            **kwargs: Additional parameters:
                     - size: Image size (e.g., "1024x1024", "512x512")
        
        Returns:
            ImageResponse with the generated image as base64.
        """
        # Get parameters (use instance defaults, override with kwargs)
        size = kwargs.get("size", self.size)
        
        try:
            # Call DeepInfra API using OpenAI-compatible endpoint
            # Following the curl example from DeepInfra documentation:
            # curl https://api.deepinfra.com/v1/openai/images/generations \
            #   -H "Content-Type: application/json" \
            #   -H "Authorization: Bearer $DEEPINFRA_API_KEY" \
            #   -d '{"prompt": "...", "size": "1024x1024", "model": "...", "n": 1}'
            response = httpx.post(
                self.__API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.model_key}",
                },
                json={
                    "prompt": prompt,
                    "size": size,
                    "model": self.model_name,
                    "n": 1,
                    "response_format": "b64_json",  # Request base64 format
                },
                timeout=120.0,  # Increased timeout for image generation
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract image data (either base64 or URL)
            # DeepInfra returns the same structure as OpenAI
            if "data" not in result or len(result["data"]) == 0:
                raise ValueError("No image data in response")
            
            image_data = result["data"][0]
            revised_prompt = image_data.get("revised_prompt", None)
            
            # Check for base64 data first, then fall back to URL
            image_base64 = image_data.get("b64_json")
            image_url = image_data.get("url")
            
            if image_base64:
                # Base64 format (preferred for FLUX models)
                return ImageResponse(
                    image_base64=image_base64,
                    revised_prompt=revised_prompt,
                    raw=result,
                )
            elif image_url:
                # URL format (used by some models like Seedream-4)
                return ImageResponse(
                    image_url=image_url,
                    revised_prompt=revised_prompt,
                    raw=result,
                )
            else:
                raise ValueError("Neither b64_json nor url found in response")
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} generating image with DeepInfra"
            try:
                error_detail = e.response.json()
                logging.error(f"{error_msg}: {error_detail}")
            except:
                logging.error(f"{error_msg}: {e.response.text}")
            # Log the request details for debugging
            logging.debug(f"Request URL: {self.__API_URL}")
            logging.debug(f"Model: {self.model_name}")
            logging.debug(f"Request body: model={self.model_name}, prompt={prompt[:50]}..., size={size}")
            raise
        except Exception as e:
            logging.error(f"Error generating image with DeepInfra: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Returns the model name."""
        return self.model_name
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns list of supported models (including aliases)."""
        return list(cls.MODEL_ALIASES.keys()) + cls.SUPPORTED_MODELS

