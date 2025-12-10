"""
ImageResponse class for image generation responses.
"""
import base64
import logging
from dataclasses import dataclass
from typing import Any, Optional


def _detect_image_type(data: bytes) -> str:
    """
    Detect image type from binary data using magic bytes.
    
    Args:
        data: Binary image data
        
    Returns:
        Image type string ("jpeg", "png", "gif", "webp", or "unknown")
    """
    if not data:
        return "unknown"
    
    # Check magic bytes
    if data.startswith(b'\xff\xd8\xff'):
        return "jpeg"
    elif data.startswith(b'\x89PNG\r\n\x1a\n'):
        return "png"
    elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return "gif"
    elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
        return "webp"
    else:
        return "unknown"


@dataclass
class ImageResponse:
    """
    Standardized structure for image generation responses across all provider subclasses.
    
    Attributes:
        image_type: Type of image data ("jpeg", "png", "url", etc.)
        image: Image data - bytes for binary data, str for URL
        revised_prompt: Optional revised prompt from the provider
        raw: Raw response data from the provider (for debugging)
    """
    image_type: str
    image: Any  # bytes for binary, str for URL
    revised_prompt: Optional[str] = None
    raw: Any = None
    
    def display_jupyter(self):
        """
        Display the image in a Jupyter notebook.
        Checks if running in Jupyter before attempting to display.
        """
        try:
            # Check if running in Jupyter
            import IPython
            ipython = IPython.get_ipython()
            if ipython is None or ipython.__class__.__name__ != 'ZMQInteractiveShell':
                logging.warning("Not running in Jupyter. Use save() to save the image instead.")
                return
            
            from IPython.display import Image, display
            
            if self.image_type == "url":
                display(Image(url=self.image))
            else:
                # For binary data, convert to base64 and use data URI format
                b64_data = base64.b64encode(self.image).decode('utf-8')
                # Use data URI format with url parameter
                data_uri = f"data:image/{self.image_type};base64,{b64_data}"
                display(Image(url=data_uri))
        except ImportError:
            logging.warning("IPython not available. Use save() to save the image instead.")
        except Exception as e:
            logging.error(f"Error displaying image in Jupyter: {e}")
    
    def save(self, filepath: Optional[str] = None) -> str:
        """
        Save the image to a file.
        
        Args:
            filepath: Optional file path. If not provided, generates a filename based on image_type.
            
        Returns:
            The filepath where the image was saved.
        """
        if self.image_type == "url":
            # Download from URL
            import httpx
            response = httpx.get(self.image)
            response.raise_for_status()
            data = response.content
            
            # Detect type from downloaded data
            detected_type = _detect_image_type(data)
            if filepath is None:
                ext = detected_type if detected_type != "unknown" else "jpg"
                filepath = f"generated_image.{ext}"
        else:
            data = self.image
            if filepath is None:
                ext = self.image_type if self.image_type != "unknown" else "jpg"
                filepath = f"generated_image.{ext}"
        
        # Ensure filepath has correct extension
        if not filepath.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            ext = self.image_type if self.image_type != "unknown" else "jpg"
            if not filepath.endswith('.'):
                filepath += f".{ext}"
        
        with open(filepath, 'wb') as f:
            f.write(data)
        
        logging.info(f"Image saved to {filepath}")
        return filepath
