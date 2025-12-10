"""
Unit tests for the t2i factory function (t2i.of).
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

import t2i
from t2i.DallEImageGenerator import DallEImageGenerator
from t2i.DeepInfraImageGenerator import DeepInfraImageGenerator
from t2i.ReplicateImageGenerator import ReplicateImageGenerator
from t2i.GeminiImageGenerator import GeminiImageGenerator
from t2i.MockImageGenerator import MockImageGenerator


class FactoryTest(unittest.TestCase):
    """Test cases for the t2i factory function."""

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

    def test_factory_function_with_z_image_turbo(self):
        """Test factory function creates ReplicateImageGenerator for z-image-turbo."""
        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-key"}):
            generator = t2i.of("z-image-turbo")
            self.assertIsInstance(generator, ReplicateImageGenerator)
            self.assertEqual(generator.get_model_name(), "prunaai/z-image-turbo")

    def test_factory_function_with_z_image_alias(self):
        """Test factory function creates ReplicateImageGenerator for z-image alias."""
        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-key"}):
            generator = t2i.of("z-image")
            self.assertIsInstance(generator, ReplicateImageGenerator)
            self.assertEqual(generator.get_model_name(), "prunaai/z-image-turbo")

    def test_factory_function_with_sd35(self):
        """Test factory function creates DeepInfraImageGenerator for sd-3.5."""
        with patch.dict(os.environ, {"DEEPINFRA_API_KEY": "test-key"}):
            generator = t2i.of("sd-3.5")
            self.assertIsInstance(generator, DeepInfraImageGenerator)
            self.assertEqual(generator.get_model_name(), "stability-ai/stable-diffusion-3.5-large")

    def test_factory_function_with_gemini25(self):
        """Test factory function creates GeminiImageGenerator for gemini-2.5."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            generator = t2i.of("gemini-2.5")
            self.assertIsInstance(generator, GeminiImageGenerator)
            self.assertEqual(generator.get_model_name(), "gemini-2.5-flash-image")

    def test_factory_function_with_nanobanana_alias(self):
        """Test factory function resolves nanobanana aliases correctly."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            generator = t2i.of("nanobanana")
            self.assertIsInstance(generator, GeminiImageGenerator)
            self.assertEqual(generator.get_model_name(), "gemini-2.5-flash-image")

    def test_factory_function_with_gemini3_image(self):
        """Test factory function creates GeminiImageGenerator for gemini-3-image alias."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            generator = t2i.of("gemini-3-image")
            self.assertIsInstance(generator, GeminiImageGenerator)
            self.assertEqual(generator.get_model_name(), "gemini-3-pro-image-preview")

    def test_factory_function_with_mock(self):
        """Test factory function creates MockImageGenerator for mock."""
        generator = t2i.of("mock")
        self.assertIsInstance(generator, MockImageGenerator)
        self.assertEqual(generator.get_model_name(), "mock")

    def test_factory_function_with_mock_alias(self):
        """Test factory function creates MockImageGenerator for mock aliases."""
        generator = t2i.of("test")
        self.assertIsInstance(generator, MockImageGenerator)
        self.assertEqual(generator.get_model_name(), "mock")

    def test_factory_function_invalid_model(self):
        """Test factory function raises RuntimeError for invalid model."""
        with self.assertRaises(RuntimeError) as context:
            t2i.of("invalid-model-name")
        self.assertIn("not supported", str(context.exception))


if __name__ == '__main__':
    unittest.main()

