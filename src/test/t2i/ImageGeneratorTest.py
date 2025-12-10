"""
Unit tests for the t2i (text-to-image) module.

This module tests the ImageGenerator implementations including:
- Factory function (t2i.of)
- Model name resolution and aliases
- Supported models listing
- Error handling for invalid models
- API key validation
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

import t2i
from t2i.DallEImageGenerator import DallEImageGenerator
from t2i.DeepInfraImageGenerator import DeepInfraImageGenerator
from t2i.ImageGenerator import ImageResponse


class ImageGeneratorTest(unittest.TestCase):
    """Test cases for ImageGenerator implementations."""

    def test_factory_function_with_dalle3(self):
        """Test factory function creates DallEImageGenerator for dall-e-3."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = t2i.of("dall-e-3")
            self.assertIsInstance(generator, DallEImageGenerator)
            self.assertEqual(generator.get_model_name(), "dall-e-3")

    def test_factory_function_with_dalle3_alias(self):
        """Test factory function resolves aliases correctly."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = t2i.of("dalle-3")
            self.assertIsInstance(generator, DallEImageGenerator)
            self.assertEqual(generator.get_model_name(), "dall-e-3")

    def test_factory_function_with_dalle2(self):
        """Test factory function creates DallEImageGenerator for dall-e-2."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = t2i.of("dall-e-2")
            self.assertIsInstance(generator, DallEImageGenerator)
            self.assertEqual(generator.get_model_name(), "dall-e-2")

    def test_factory_function_with_dalle2_alias(self):
        """Test factory function resolves dall-e-2 aliases."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = t2i.of("dalle-2")
            self.assertIsInstance(generator, DallEImageGenerator)
            self.assertEqual(generator.get_model_name(), "dall-e-2")

    def test_factory_function_with_flux2(self):
        """Test factory function creates DeepInfraImageGenerator for flux-2."""
        with patch.dict(os.environ, {"DEEPINFRA_API_KEY": "test-key"}):
            generator = t2i.of("flux-2")
            self.assertIsInstance(generator, DeepInfraImageGenerator)
            self.assertEqual(generator.get_model_name(), "black-forest-labs/FLUX-2-pro")

    def test_factory_function_with_seedream4(self):
        """Test factory function creates DeepInfraImageGenerator for seedream-4."""
        with patch.dict(os.environ, {"DEEPINFRA_API_KEY": "test-key"}):
            generator = t2i.of("seedream-4")
            self.assertIsInstance(generator, DeepInfraImageGenerator)
            self.assertEqual(generator.get_model_name(), "ByteDance/Seedream-4")

    def test_factory_function_with_sd35(self):
        """Test factory function creates DeepInfraImageGenerator for sd-3.5."""
        with patch.dict(os.environ, {"DEEPINFRA_API_KEY": "test-key"}):
            generator = t2i.of("sd-3.5")
            self.assertIsInstance(generator, DeepInfraImageGenerator)
            self.assertEqual(generator.get_model_name(), "stability-ai/stable-diffusion-3.5-large")

    def test_factory_function_invalid_model(self):
        """Test factory function raises RuntimeError for invalid model."""
        with self.assertRaises(RuntimeError) as context:
            t2i.of("invalid-model-name")
        self.assertIn("not supported", str(context.exception))

    def test_dalle_get_supported_models(self):
        """Test DallEImageGenerator.get_supported_models returns all models and aliases."""
        models = DallEImageGenerator.get_supported_models()
        self.assertIn("dall-e-3", models)
        self.assertIn("dall-e-2", models)
        self.assertIn("dalle-3", models)
        self.assertIn("dalle-2", models)
        self.assertIn("dalle3", models)
        self.assertIn("dalle2", models)

    def test_deepinfra_get_supported_models(self):
        """Test DeepInfraImageGenerator.get_supported_models returns all models and aliases."""
        models = DeepInfraImageGenerator.get_supported_models()
        self.assertIn("black-forest-labs/FLUX-2-pro", models)
        self.assertIn("flux-2", models)
        self.assertIn("ByteDance/Seedream-4", models)
        self.assertIn("seedream-4", models)
        self.assertIn("stability-ai/stable-diffusion-3.5-large", models)
        self.assertIn("sd-3.5", models)

    def test_dalle_init_with_canonical_name(self):
        """Test DallEImageGenerator initialization with canonical model name."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key")
            self.assertEqual(generator.get_model_name(), "dall-e-3")

    def test_dalle_init_with_alias(self):
        """Test DallEImageGenerator initialization with alias."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dalle-3", model_key="test-key")
            self.assertEqual(generator.get_model_name(), "dall-e-3")

    def test_dalle_init_invalid_model(self):
        """Test DallEImageGenerator raises ValueError for invalid model."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with self.assertRaises(ValueError) as context:
                DallEImageGenerator("invalid-model", model_key="test-key")
            self.assertIn("not supported", str(context.exception))

    def test_dalle_init_missing_api_key(self):
        """Test DallEImageGenerator raises RuntimeError when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                DallEImageGenerator("dall-e-3")
            self.assertIn("API key", str(context.exception))

    def test_dalle_init_with_api_key_parameter(self):
        """Test DallEImageGenerator accepts API key as parameter."""
        generator = DallEImageGenerator("dall-e-3", model_key="test-key-123")
        self.assertEqual(generator.model_key, "test-key-123")

    def test_deepinfra_init_with_canonical_name(self):
        """Test DeepInfraImageGenerator initialization with canonical model name."""
        generator = DeepInfraImageGenerator("black-forest-labs/FLUX-2-pro", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "black-forest-labs/FLUX-2-pro")

    def test_deepinfra_init_with_alias(self):
        """Test DeepInfraImageGenerator initialization with alias."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "black-forest-labs/FLUX-2-pro")

    def test_deepinfra_init_invalid_model(self):
        """Test DeepInfraImageGenerator raises ValueError for invalid model."""
        with self.assertRaises(ValueError) as context:
            DeepInfraImageGenerator("invalid-model", model_key="test-key")
        self.assertIn("not supported", str(context.exception))

    def test_deepinfra_init_missing_api_key(self):
        """Test DeepInfraImageGenerator raises RuntimeError when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                DeepInfraImageGenerator("flux-2")
            self.assertIn("API key", str(context.exception))

    def test_deepinfra_init_with_api_key_parameter(self):
        """Test DeepInfraImageGenerator accepts API key as parameter."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key-456")
        self.assertEqual(generator.model_key, "test-key-456")

    def test_dalle_default_size(self):
        """Test DallEImageGenerator uses default size from model config."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            generator = DallEImageGenerator("dall-e-3", model_key="test-key")
            self.assertEqual(generator.size, "1024x1024")

    def test_dalle_custom_size(self):
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

    def test_deepinfra_default_size(self):
        """Test DeepInfraImageGenerator uses default size from model config."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key")
        self.assertEqual(generator.size, "1024x1024")

    def test_deepinfra_custom_size(self):
        """Test DeepInfraImageGenerator accepts custom size."""
        generator = DeepInfraImageGenerator("flux-2", model_key="test-key", size="512x512")
        self.assertEqual(generator.size, "512x512")

    def test_image_response_structure(self):
        """Test ImageResponse dataclass structure."""
        response = ImageResponse(
            image_url="https://example.com/image.png",
            image_base64=None,
            revised_prompt="A revised prompt",
            raw={"test": "data"}
        )
        self.assertEqual(response.image_url, "https://example.com/image.png")
        self.assertIsNone(response.image_base64)
        self.assertEqual(response.revised_prompt, "A revised prompt")
        self.assertEqual(response.raw, {"test": "data"})

    def test_image_response_with_base64(self):
        """Test ImageResponse with base64 data."""
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = ImageResponse(
            image_url=None,
            image_base64=base64_data,
            revised_prompt=None,
            raw=None
        )
        self.assertIsNone(response.image_url)
        self.assertEqual(response.image_base64, base64_data)
        self.assertIsNone(response.revised_prompt)

    @patch('openai.OpenAI')
    def test_dalle3_generate_success(self, mock_openai_class):
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
        self.assertEqual(response.image_url, "https://example.com/image.png")
        self.assertEqual(response.revised_prompt, "A revised prompt")
        mock_client.images.generate.assert_called_once()

    @patch('httpx.post')
    def test_deepinfra_generate_success_with_base64(self, mock_httpx_post):
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
        self.assertIsNotNone(response.image_base64)
        self.assertIsNone(response.image_url)
        mock_httpx_post.assert_called_once()

    @patch('httpx.post')
    def test_deepinfra_generate_success_with_url(self, mock_httpx_post):
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
        self.assertEqual(response.image_url, "https://example.com/image.png")
        self.assertIsNone(response.image_base64)
        self.assertEqual(response.revised_prompt, "A revised prompt")

    @patch('httpx.post')
    def test_deepinfra_generate_no_data(self, mock_httpx_post):
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
    def test_deepinfra_generate_http_error(self, mock_httpx_post):
        """Test DeepInfraImageGenerator.generate() handles HTTP errors."""
        import httpx
        
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

