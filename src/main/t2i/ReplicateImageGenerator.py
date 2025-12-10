"""
Replicate image generation implementation.
Supports Replicate's text-to-image models.
"""
import base64
import logging
import os
from typing import List

import replicate

from t2i.ImageGenerator import ImageGenerator
from t2i.ImageResponse import ImageResponse, _detect_image_type


def _is_base64_string(s: str) -> bool:
    """
    Check if a string is base64-encoded data.
    
    Args:
        s: String to check
        
    Returns:
        True if the string appears to be base64-encoded
    """
    if not isinstance(s, str):
        return False
    
    # Remove whitespace for checking
    s_clean = s.strip()
    
    # Base64 strings are typically longer (at least 100 chars for images)
    # Check if it starts with base64-encoded JPEG magic bytes (/9j/)
    # This is the most reliable indicator for image data
    if s_clean.startswith('/9j/'):
        return True
    
    # For other cases, check if it's a long base64-like string
    if len(s_clean) > 100:
        # Check if it contains mostly base64 characters
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        non_base64_count = sum(1 for c in s_clean if c not in base64_chars and not c.isspace())
        # Allow some non-base64 chars (like whitespace, but not too many)
        if non_base64_count < len(s_clean) * 0.1:  # Less than 10% non-base64 chars
            # Try to decode a sample to verify it's valid base64
            try:
                # Take first 200 chars and pad if needed
                sample = s_clean[:200].replace(' ', '').replace('\n', '').replace('\r', '')
                # Pad to multiple of 4
                padding = (4 - len(sample) % 4) % 4
                sample += '=' * padding
                base64.b64decode(sample, validate=True)
                return True
            except Exception:
                return False
    
    return False


def _is_url(s: str) -> bool:
    """
    Check if a string is a URL.
    
    Args:
        s: String to check
        
    Returns:
        True if the string appears to be a URL
    """
    if not isinstance(s, str):
        return False
    
    # Simple URL check - starts with http:// or https://
    return s.startswith('http://') or s.startswith('https://')


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
                # Binary image data - combine all chunks
                image_data = b''.join(chunks)
                image_type = _detect_image_type(image_data)
                
                return ImageResponse(
                    image_type=image_type,
                    image=image_data,
                    revised_prompt=None,  # Replicate doesn't provide revised prompts
                    raw=chunks,  # Store all chunks as raw data
                )
            elif isinstance(first_chunk, str):
                # String data - could be URL or base64-encoded image
                if len(chunks) == 1:
                    data_str = chunks[0]
                else:
                    # Multiple chunks - combine them (for base64 strings that might be split)
                    data_str = ''.join(chunks)
                
                # Check if it's base64-encoded image data
                if _is_base64_string(data_str):
                    # Decode base64 to bytes
                    try:
                        image_data = base64.b64decode(data_str)
                        image_type = _detect_image_type(image_data)
                        
                        return ImageResponse(
                            image_type=image_type,
                            image=image_data,
                            revised_prompt=None,  # Replicate doesn't provide revised prompts
                            raw=chunks,  # Store all chunks as raw data
                        )
                    except Exception as e:
                        logging.warning(f"Failed to decode base64 string: {e}. Treating as URL.")
                        # Fall through to URL handling
                
                # Check if it's a URL
                if _is_url(data_str):
                    return ImageResponse(
                        image_type="url",
                        image=data_str,
                        revised_prompt=None,  # Replicate doesn't provide revised prompts
                        raw=chunks,  # Store all chunks as raw data
                    )
                
                # If we can't determine, assume it's a URL (legacy behavior)
                logging.warning(f"Unrecognized string format from Replicate, treating as URL: {data_str[:50]}...")
                return ImageResponse(
                    image_type="url",
                    image=data_str,
                    revised_prompt=None,  # Replicate doesn't provide revised prompts
                    raw=chunks,  # Store all chunks as raw data
                )
            else:
                # Unexpected type
                raise ValueError(f"Unexpected data type from Replicate: {type(first_chunk)}")
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

