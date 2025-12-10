"""
Unit tests for DeepInfraImageGenerator.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

from t2i.DeepInfraImageGenerator import DeepInfraImageGenerator
from t2i.ImageResponse import ImageResponse


class DeepInfraImageGeneratorTest(unittest.TestCase):
    """Test cases for DeepInfraImageGenerator."""

    def test_get_supported_models(self):
        """Test DeepInfraImageGenerator.get_supported_models returns all models and aliases."""
        models = DeepInfraImageGenerator.get_supported_models()
        self.assertIn("black-forest-labs/FLUX-2-pro", models)
        self.assertIn("flux-2", models)
        self.assertIn("ByteDance/Seedream-4", models)
        self.assertIn("seedream-4", models)
        self.assertIn("stability-ai/stable-diffusion-3.5-large", models)
        self.assertIn("sd-3.5", models)

    def test_init_with_canonical_name(self):
        """Test DeepInfraImageGenerator initialization with canonical model name."""
        generator = DeepInfraImageGenerator("black-forest-labs/FLUX-2-pro", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "black-forest-labs/FLUX-2-pro")

    def test_init_with_alias(self):
        """Test DeepInfraImageGenerator initialization with alias."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "black-forest-labs/FLUX-2-pro")

    def test_init_invalid_model(self):
        """Test DeepInfraImageGenerator raises ValueError for invalid model."""
        with self.assertRaises(ValueError) as context:
            DeepInfraImageGenerator("invalid-model", model_key="test-key")
        self.assertIn("not supported", str(context.exception))

    def test_init_missing_api_key(self):
        """Test DeepInfraImageGenerator raises RuntimeError when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                DeepInfraImageGenerator("flux-2")
            self.assertIn("API key", str(context.exception))

    def test_init_with_api_key_parameter(self):
        """Test DeepInfraImageGenerator accepts API key as parameter."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key-456")
        self.assertEqual(generator.model_key, "test-key-456")

    def test_default_size(self):
        """Test DeepInfraImageGenerator uses default size from model config."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        self.assertEqual(generator.size, "1024x1024")

    def test_custom_size(self):
        """Test DeepInfraImageGenerator accepts custom size."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key", size="512x512")
        self.assertEqual(generator.size, "512x512")

    @patch('httpx.post')
    def test_generate_success_with_base64(self, mock_httpx_post):
        """Test DeepInfraImageGenerator.generate() with base64 response."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{
                "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "revised_prompt": None
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_post.return_value = mock_response
        
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertIn(response.image_type, ["jpeg", "png", "unknown"])  # Detected type
        self.assertIsInstance(response.image, bytes)
        mock_httpx_post.assert_called_once()

    @patch('httpx.post')
    def test_generate_success_with_url(self, mock_httpx_post):
        """Test DeepInfraImageGenerator.generate() with URL response."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{
                "url": "https://example.com/image.png",
                "revised_prompt": "A revised prompt"
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_post.return_value = mock_response
        
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "url")
        self.assertEqual(response.image, "https://example.com/image.png")
        self.assertEqual(response.revised_prompt, "A revised prompt")

    @patch('httpx.post')
    def test_generate_no_data(self, mock_httpx_post):
        """Test DeepInfraImageGenerator.generate() raises ValueError when no data in response."""
        # Mock HTTP response with no data
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_post.return_value = mock_response
        
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        with self.assertRaises(ValueError) as context:
            generator.generate("A test prompt")
        self.assertIn("No image data", str(context.exception))

    @patch('httpx.post')
    def test_generate_http_error(self, mock_httpx_post):
        """Test DeepInfraImageGenerator.generate() handles HTTP errors."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_response.text = "Bad request"
        mock_httpx_post.side_effect = httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=mock_response
        )
        
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        with self.assertRaises(httpx.HTTPStatusError):
            generator.generate("A test prompt")


if __name__ == '__main__':
    unittest.main()

