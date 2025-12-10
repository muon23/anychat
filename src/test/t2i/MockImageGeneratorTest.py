"""
Unit tests for MockImageGenerator.
"""
import sys
import unittest
from pathlib import Path

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

from t2i.MockImageGenerator import MockImageGenerator
from t2i.ImageResponse import ImageResponse


class MockImageGeneratorTest(unittest.TestCase):
    """Test cases for MockImageGenerator."""

    def test_get_supported_models(self):
        """Test MockImageGenerator.get_supported_models() returns correct models."""
        models = MockImageGenerator.get_supported_models()
        self.assertIn("mock", models)
        self.assertIn("test", models)
        self.assertIn("placeholder", models)
        self.assertIn("mock-image", models)

    def test_init_with_canonical_name(self):
        """Test MockImageGenerator initialization with canonical model name."""
        generator = MockImageGenerator("mock")
        self.assertEqual(generator.get_model_name(), "mock")

    def test_init_with_alias(self):
        """Test MockImageGenerator initialization with alias."""
        generator = MockImageGenerator("test")
        self.assertEqual(generator.get_model_name(), "mock")

    def test_init_invalid_model(self):
        """Test MockImageGenerator raises ValueError for invalid model."""
        with self.assertRaises(ValueError) as context:
            MockImageGenerator("invalid-model")
        self.assertIn("not supported", str(context.exception))

    def test_generate_returns_image_response(self):
        """Test MockImageGenerator.generate() returns ImageResponse with URL."""
        generator = MockImageGenerator("mock")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "url")
        self.assertIsInstance(response.image, str)
        self.assertIn("cursor", response.image.lower())
        self.assertIsNotNone(response.revised_prompt)
        self.assertIn("[Mock]", response.revised_prompt)
        self.assertIsNotNone(response.raw)
        self.assertTrue(response.raw.get("mock", False))

    def test_generate_with_different_prompts(self):
        """Test MockImageGenerator.generate() works with different prompts."""
        generator = MockImageGenerator("mock")
        
        response1 = generator.generate("A cat")
        response2 = generator.generate("A dog")
        
        # Both should return valid responses
        self.assertIsInstance(response1, ImageResponse)
        self.assertIsInstance(response2, ImageResponse)
        # Both should have the same URL (mock doesn't vary by prompt)
        self.assertEqual(response1.image, response2.image)
        # But revised prompts should be different
        self.assertIn("A cat", response1.revised_prompt)
        self.assertIn("A dog", response2.revised_prompt)


if __name__ == '__main__':
    unittest.main()

