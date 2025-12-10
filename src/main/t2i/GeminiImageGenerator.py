"""
Google Gemini Image Generation implementation using LangChain.
"""
import base64
import logging
import os
from typing import List

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI, Modality

from t2i.ImageGenerator import ImageGenerator
from t2i.ImageResponse import ImageResponse, _detect_image_type


class GeminiImageGenerator(ImageGenerator):
    """
    Concrete implementation for Google's Gemini Image Generation using LangChain.
    Supports gemini-2.5-flash-image and gemini-3-pro-image-preview models.
    """
    
    # Model metadata
    __MODELS = {
        "gemini-2.5-flash-image": {
            "aliases": ["gemini-2.5", "nanobanana", "nano-banana", "gemini-2.5-image", "flash-image"],
        },
        "gemini-3-pro-image-preview": {
            "aliases": ["gemini-3", "gemini-3-image", "gemini-3-pro-image", "gemini-3-preview"],
        },
    }
    
    # List of all canonical model names
    SUPPORTED_MODELS = list(__MODELS.keys())
    
    MODEL_ALIASES = ImageGenerator._alias2model(__MODELS)
    
    def __init__(self, model_name: str = "gemini-2.5", model_key: str = None, **kwargs):
        """
        Initializes the Gemini image generator.
        
        Args:
            model_name: The model to use (defaults to "gemini-2.5" alias which maps to gemini-2.5-flash-image).
            model_key: The Google API key. Searches environment variable if None.
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
            raise ValueError(f"Gemini model {model_name} not supported. Supported: {self.SUPPORTED_MODELS}")
        
        logging.info(f"Using Gemini model: {self.model_name}")
        
        # API Key management - prefer GEMINI_API_KEY over GOOGLE_API_KEY
        if model_key:
            self.model_key = model_key
        else:
            # Check GEMINI_API_KEY first, then fall back to GOOGLE_API_KEY
            self.model_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if not self.model_key:
            raise RuntimeError("Google API key not provided (set GEMINI_API_KEY or GOOGLE_API_KEY)")
        
        # Initialize LangChain ChatGoogleGenerativeAI with image modality
        # Pass API key via google_api_key parameter to avoid environment variable conflicts
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.model_key,
            response_modalities=[Modality.IMAGE],
        )
    
    def generate(self, prompt: str, **kwargs) -> ImageResponse:
        """
        Generates an image using Google's Gemini Image Generation.
        
        Args:
            prompt: The text description of the image to generate.
            **kwargs: Additional parameters (currently unused).
        
        Returns:
            ImageResponse with the generated image as bytes.
        """
        try:
            # Create a HumanMessage with the prompt
            message = HumanMessage(content=prompt)
            
            # Invoke the model
            response = self.llm.invoke([message])
            
            # Process the response
            # The image data is returned as base64 encoded text within the response
            # Log response structure for debugging
            logging.debug(f"Response type: {type(response)}")
            logging.debug(f"Response content type: {type(response.content)}")
            logging.debug(f"Response content: {response.content}")
            
            # Check if response has content attribute
            content = getattr(response, 'content', None)
            if not content:
                logging.warning(f"Response has no content attribute. Response: {response}")
                raise ValueError("No content in response")
            
            # Handle different content formats
            if isinstance(content, list):
                logging.debug(f"Content is a list with {len(content)} items")
                for i, content_part in enumerate(content):
                    logging.debug(f"Processing content part {i}: type={type(content_part)}")
                    
                    # Try to extract image data from various possible formats
                    base64_data = None
                    
                    # Format 1: Dict with "type": "image" and "base64_data"
                    # Format 1b: Dict with "type": "image_url" and "image_url" containing data URI
                    if isinstance(content_part, dict):
                        logging.debug(f"  Part is dict with keys: {list(content_part.keys())}")
                        part_type = content_part.get("type")
                        
                        if part_type == "image":
                            base64_data = content_part.get("base64_data")
                            if base64_data:
                                logging.debug("  Found image in dict format with base64_data")
                        elif part_type == "image_url":
                            # Handle image_url format with data URI
                            image_url_dict = content_part.get("image_url")
                            if isinstance(image_url_dict, dict):
                                url = image_url_dict.get("url", "")
                                if url.startswith("data:image/"):
                                    # Extract base64 from data URI: data:image/png;base64,<base64_data>
                                    # Format: data:image/<type>;base64,<base64_string>
                                    try:
                                        # Split by comma to get the base64 part
                                        base64_data = url.split(",", 1)[1] if "," in url else None
                                        if base64_data:
                                            logging.debug("  Found image_url with data URI, extracted base64")
                                    except Exception as e:
                                        logging.warning(f"  Failed to extract base64 from data URI: {e}")
                                        base64_data = None
                                else:
                                    # Regular URL, not base64
                                    logging.debug(f"  Found image_url with regular URL: {url[:50]}...")
                                    base64_data = None
                            else:
                                base64_data = None
                    
                    # Format 2: Object with type attribute
                    elif hasattr(content_part, "type"):
                        part_type = getattr(content_part, "type", None)
                        logging.debug(f"  Part has type attribute: {part_type}")
                        if part_type == "image":
                            if hasattr(content_part, "base64_data"):
                                base64_data = content_part.base64_data
                            elif hasattr(content_part, "data"):
                                base64_data = content_part.data
                            if base64_data:
                                logging.debug("  Found image in object format")
                    
                    # Format 3: Check if it's a LangChain ImageBlock or similar
                    elif hasattr(content_part, "__class__"):
                        class_name = content_part.__class__.__name__
                        logging.debug(f"  Part is {class_name}")
                        # Try common attribute names
                        if hasattr(content_part, "base64_data"):
                            base64_data = content_part.base64_data
                        elif hasattr(content_part, "data"):
                            base64_data = content_part.data
                        elif hasattr(content_part, "image"):
                            # Might be an ImageBlock with .image attribute
                            img_obj = content_part.image
                            if hasattr(img_obj, "base64_data"):
                                base64_data = img_obj.base64_data
                            elif hasattr(img_obj, "data"):
                                base64_data = img_obj.data
                    
                    # If we found base64 data, decode and return
                    if base64_data:
                        try:
                            image_bytes = base64.b64decode(base64_data)
                            image_type = _detect_image_type(image_bytes)
                            
                            logging.info(f"Successfully extracted image: type={image_type}, size={len(image_bytes)} bytes")
                            return ImageResponse(
                                image_type=image_type,
                                image=image_bytes,
                                revised_prompt=None,
                                raw=response,
                            )
                        except Exception as e:
                            logging.warning(f"Failed to decode base64 data: {e}")
                            continue
            else:
                # Content might be a single item, not a list
                logging.debug(f"Content is not a list, type: {type(content)}")
                # Try to extract from single content item
                if hasattr(content, "base64_data"):
                    base64_data = content.base64_data
                elif isinstance(content, str):
                    # Might be base64 string directly
                    try:
                        image_bytes = base64.b64decode(content)
                        image_type = _detect_image_type(image_bytes)
                        return ImageResponse(
                            image_type=image_type,
                            image=image_bytes,
                            revised_prompt=None,
                            raw=response,
                        )
                    except:
                        pass
            
            # If we get here, we couldn't find image data
            logging.error(f"Could not extract image data from response. Content structure: {content}")
            logging.error(f"Full response: {response}")
            raise ValueError("No image data found in response")
        except Exception as e:
            logging.error(f"Error generating image with Gemini: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Returns the model name."""
        return self.model_name
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Returns list of supported models (including aliases)."""
        return list(cls.MODEL_ALIASES.keys()) + cls.SUPPORTED_MODELS

