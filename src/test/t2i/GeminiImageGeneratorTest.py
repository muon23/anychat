"""
Unit tests for GeminiImageGenerator.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import base64

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

from t2i.GeminiImageGenerator import GeminiImageGenerator
from t2i.ImageResponse import ImageResponse


class GeminiImageGeneratorTest(unittest.TestCase):
    """Test cases for GeminiImageGenerator."""

    def test_get_supported_models(self):
        """Test GeminiImageGenerator.get_supported_models() returns correct models."""
        models = GeminiImageGenerator.get_supported_models()
        self.assertIn("gemini-2.5-flash-image", models)
        self.assertIn("gemini-3-pro-image-preview", models)
        self.assertIn("nanobanana", models)
        self.assertIn("nano-banana", models)
        self.assertIn("gemini-3-image", models)

    def test_init_with_model_key(self):
        """Test GeminiImageGenerator initialization with model_key."""
        generator = GeminiImageGenerator("gemini-2.5-flash-image", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "gemini-2.5-flash-image")

    def test_init_with_env_key(self):
        """Test GeminiImageGenerator initialization with environment variable."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key"}):
            generator = GeminiImageGenerator("gemini-2.5-flash-image")
            self.assertEqual(generator.get_model_name(), "gemini-2.5-flash-image")

    def test_init_no_api_key(self):
        """Test GeminiImageGenerator raises RuntimeError when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                GeminiImageGenerator("gemini-2.5-flash-image")
            self.assertIn("Google API key", str(context.exception))

    def test_init_invalid_model(self):
        """Test GeminiImageGenerator raises ValueError for invalid model."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(ValueError) as context:
                GeminiImageGenerator("invalid-model")
            self.assertIn("not supported", str(context.exception))

    @patch('t2i.GeminiImageGenerator.ChatGoogleGenerativeAI')
    def test_generate_success(self, mock_chat_class):
        """Test GeminiImageGenerator.generate() with successful response."""
        # Create mock image data
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100
        base64_data = base64.b64encode(jpeg_data).decode('utf-8')
        
        # Mock the LangChain response structure with image_url format
        mock_response = MagicMock()
        mock_response.content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_data}"
                }
            }
        ]
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm
        
        generator = GeminiImageGenerator("gemini-2.5-flash-image", model_key="test-key")
        # Replace the llm with our mock
        generator.llm = mock_llm
        
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "jpeg")
        self.assertIsInstance(response.image, bytes)
        self.assertEqual(response.image, jpeg_data)
        mock_llm.invoke.assert_called_once()

    @patch('t2i.GeminiImageGenerator.ChatGoogleGenerativeAI')
    def test_generate_no_image_data(self, mock_chat_class):
        """Test GeminiImageGenerator.generate() raises ValueError when no image in response."""
        # Mock response with content but no image data
        # Use a list with non-image content to trigger "No image data found in response"
        mock_response = MagicMock()
        mock_response.content = [
            {
                "type": "text",
                "text": "Some text response"
            }
        ]
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm
        
        generator = GeminiImageGenerator("gemini-2.5-flash-image", model_key="test-key")
        generator.llm = mock_llm
        
        with self.assertRaises(ValueError) as context:
            generator.generate("A test prompt")
        self.assertIn("No image data", str(context.exception))
    
    @patch('t2i.GeminiImageGenerator.ChatGoogleGenerativeAI')
    def test_generate_no_content(self, mock_chat_class):
        """Test GeminiImageGenerator.generate() raises ValueError when response has no content."""
        # Mock response with no content attribute or empty content
        mock_response = MagicMock()
        mock_response.content = []  # Empty list
        
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_class.return_value = mock_llm
        
        generator = GeminiImageGenerator("gemini-2.5-flash-image", model_key="test-key")
        generator.llm = mock_llm
        
        with self.assertRaises(ValueError) as context:
            generator.generate("A test prompt")
        # Empty list triggers "No content in response"
        self.assertIn("No content", str(context.exception))

    @patch('t2i.GeminiImageGenerator.ChatGoogleGenerativeAI')
    def test_generate_with_exception(self, mock_chat_class):
        """Test GeminiImageGenerator.generate() handles exceptions."""
        # Mock LLM to raise an exception
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")
        mock_chat_class.return_value = mock_llm
        
        generator = GeminiImageGenerator("gemini-2.5-flash-image", model_key="test-key")
        generator.llm = mock_llm
        
        with self.assertRaises(Exception) as context:
            generator.generate("A test prompt")
        self.assertIn("API error", str(context.exception))


if __name__ == '__main__':
    unittest.main()

