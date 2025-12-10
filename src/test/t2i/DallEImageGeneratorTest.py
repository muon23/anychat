"""
Unit tests for DallEImageGenerator.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

from t2i.DallEImageGenerator import DallEImageGenerator
from t2i.ImageResponse import ImageResponse


class DallEImageGeneratorTest(unittest.TestCase):
    """Test cases for DallEImageGenerator."""

    def test_get_supported_models(self):
        """Test DallEImageGenerator.get_supported_models returns all models and aliases."""
        models = DallEImageGenerator.get_supported_models()
        self.assertIn("dall-e-3", models)
        self.assertIn("dall-e-2", models)
        self.assertIn("dalle-3", models)
        self.assertIn("dalle-2", models)
        self.assertIn("dalle3", models)
        self.assertIn("dalle2", models)

    def test_init_with_canonical_name(self):
        """Test DallEImageGenerator initialization with canonical model name."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key")
            self.assertEqual(generator.get_model_name(), "dall-e-3")

    def test_init_with_alias(self):
        """Test DallEImageGenerator initialization with alias."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dalle-3", model_key="test-key")
            self.assertEqual(generator.get_model_name(), "dall-e-3")

    def test_init_invalid_model(self):
        """Test DallEImageGenerator raises ValueError for invalid model."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with self.assertRaises(ValueError) as context:
                DallEImageGenerator("invalid-model", model_key="test-key")
            self.assertIn("not supported", str(context.exception))

    def test_init_missing_api_key(self):
        """Test DallEImageGenerator raises RuntimeError when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                DallEImageGenerator("dall-e-3")
            self.assertIn("API key", str(context.exception))

    def test_init_with_api_key_parameter(self):
        """Test DallEImageGenerator accepts API key as parameter."""
        generator = DallEImageGenerator("dall-e-3", model_key="test-key-123")
        self.assertEqual(generator.model_key, "test-key-123")

    def test_default_size(self):
        """Test DallEImageGenerator uses default size from model config."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key")
            self.assertEqual(generator.size, "1024x1024")

    def test_custom_size(self):
        """Test DallEImageGenerator accepts custom size."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key", size="512x512")
            self.assertEqual(generator.size, "512x512")

    def test_dalle3_default_quality_and_style(self):
        """Test DallEImageGenerator uses default quality and style for dall-e-3."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key")
            self.assertEqual(generator.quality, "standard")
            self.assertEqual(generator.style, "vivid")

    def test_dalle3_custom_quality_and_style(self):
        """Test DallEImageGenerator accepts custom quality and style for dall-e-3."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key", quality="hd", style="natural")
            self.assertEqual(generator.quality, "hd")
            self.assertEqual(generator.style, "natural")

    def test_dalle2_no_quality_or_style(self):
        """Test DallEImageGenerator doesn't set quality/style for dall-e-2."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-2", model_key="test-key")
            self.assertIsNone(generator.quality)
            self.assertIsNone(generator.style)

    @patch('openai.OpenAI')
    def test_generate_success(self, mock_openai_class):
        """Test DallEImageGenerator.generate() for dall-e-3 with successful response."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].url = "https://example.com/image.png"
        mock_response.data[0].revised_prompt = "A revised prompt"
        mock_client.images.generate.return_value = mock_response
        
        generator = DallEImageGenerator("dall-e-3", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "url")
        self.assertEqual(response.image, "https://example.com/image.png")
        self.assertEqual(response.revised_prompt, "A revised prompt")
        mock_client.images.generate.assert_called_once()


if __name__ == '__main__':
    unittest.main()

