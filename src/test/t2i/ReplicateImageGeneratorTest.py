"""
Unit tests for ReplicateImageGenerator.
"""
import base64
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

from t2i.ReplicateImageGenerator import ReplicateImageGenerator
from t2i.ImageResponse import ImageResponse


class ReplicateImageGeneratorTest(unittest.TestCase):
    """Test cases for ReplicateImageGenerator."""

    def test_get_supported_models(self):
        """Test ReplicateImageGenerator.get_supported_models returns all models and aliases."""
        models = ReplicateImageGenerator.get_supported_models()
        self.assertIn("prunaai/z-image-turbo", models)
        self.assertIn("z-image", models)
        self.assertIn("z-image-turbo", models)

    def test_init_with_canonical_name(self):
        """Test ReplicateImageGenerator initialization with canonical model name."""
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "prunaai/z-image-turbo")

    def test_init_with_alias(self):
        """Test ReplicateImageGenerator initialization with alias."""
        generator = ReplicateImageGenerator("z-image", model_key="test-key")
        self.assertEqual(generator.get_model_name(), "prunaai/z-image-turbo")

    def test_init_invalid_model(self):
        """Test ReplicateImageGenerator raises ValueError for invalid model."""
        with self.assertRaises(ValueError) as context:
            ReplicateImageGenerator("invalid-model", model_key="test-key")
        self.assertIn("not supported", str(context.exception))

    def test_init_missing_api_key(self):
        """Test ReplicateImageGenerator raises RuntimeError when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as context:
                ReplicateImageGenerator("prunaai/z-image-turbo")
            self.assertIn("API token", str(context.exception))

    def test_init_with_api_key_parameter(self):
        """Test ReplicateImageGenerator accepts API key as parameter."""
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key-789")
        self.assertEqual(generator.model_key, "test-key-789")

    @patch('replicate.run')
    def test_generate_success_with_string_url(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with string URL response."""
        # Mock Replicate response - single URL string
        mock_replicate_run.return_value = "https://example.com/image.png"
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "url")
        self.assertEqual(response.image, "https://example.com/image.png")
        self.assertIsNone(response.revised_prompt)
        mock_replicate_run.assert_called_once()

    @patch('replicate.run')
    def test_generate_success_with_binary_data(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with binary image data response."""
        # Mock Replicate response - binary JPEG data
        jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        mock_replicate_run.return_value = jpeg_header + b'\x00' * 100  # Simulate JPEG data
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "jpeg")
        self.assertIsInstance(response.image, bytes)
        self.assertEqual(response.image[:len(jpeg_header)], jpeg_header)

    @patch('replicate.run')
    def test_generate_success_with_base64_string(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with base64-encoded string response."""
        # Create a base64-encoded JPEG (starts with /9j/ when base64 encoded)
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100
        base64_str = base64.b64encode(jpeg_data).decode('utf-8')
        
        # Mock Replicate response - base64 string
        mock_replicate_run.return_value = base64_str
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "jpeg")
        self.assertIsInstance(response.image, bytes)
        self.assertEqual(response.image, jpeg_data)

    @patch('replicate.run')
    def test_generate_success_with_list_url(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with list of URLs response."""
        # Mock Replicate response - list of URLs
        mock_replicate_run.return_value = ["https://example.com/image1.png", "https://example.com/image2.png"]
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "url")
        self.assertEqual(response.image, "https://example.com/image1.png")
        self.assertIsNone(response.revised_prompt)

    @patch('replicate.run')
    def test_generate_success_with_list_binary(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with list of binary data."""
        # Mock Replicate response - list with binary data
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100
        mock_replicate_run.return_value = [jpeg_data]
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "jpeg")
        self.assertIsInstance(response.image, bytes)
        self.assertEqual(len(response.image), len(jpeg_data))

    @patch('replicate.run')
    def test_generate_success_with_generator(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with generator response."""
        # Mock Replicate response - generator that yields URLs
        def url_generator():
            yield "https://example.com/image.png"
        mock_replicate_run.return_value = url_generator()
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "url")
        self.assertEqual(response.image, "https://example.com/image.png")

    @patch('replicate.run')
    def test_generate_success_with_generator_binary(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() with generator yielding binary data."""
        # Mock Replicate response - generator that yields binary data
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100
        def binary_generator():
            yield jpeg_data
        mock_replicate_run.return_value = binary_generator()
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        response = generator.generate("A test prompt")
        
        self.assertIsInstance(response, ImageResponse)
        self.assertEqual(response.image_type, "jpeg")
        self.assertIsInstance(response.image, bytes)
        self.assertEqual(len(response.image), len(jpeg_data))

    @patch('replicate.run')
    def test_generate_no_data(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() raises ValueError when no data in response."""
        # Mock Replicate response with no data
        mock_replicate_run.return_value = []
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        with self.assertRaises(ValueError) as context:
            generator.generate("A test prompt")
        self.assertIn("No image data", str(context.exception))

    @patch('replicate.run')
    def test_generate_with_exception(self, mock_replicate_run):
        """Test ReplicateImageGenerator.generate() handles exceptions."""
        # Mock Replicate to raise an exception
        mock_replicate_run.side_effect = Exception("API error")
        
        generator = ReplicateImageGenerator("prunaai/z-image-turbo", model_key="test-key")
        with self.assertRaises(Exception) as context:
            generator.generate("A test prompt")
        self.assertIn("API error", str(context.exception))


if __name__ == '__main__':
    unittest.main()

