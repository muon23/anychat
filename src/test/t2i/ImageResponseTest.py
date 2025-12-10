"""
Unit tests for ImageResponse.
"""
import sys
import unittest
from pathlib import Path

# Add src/main to path
project_root = Path(__file__).parent.parent.parent.parent
src_main = project_root / 'src' / 'main'
sys.path.insert(0, str(src_main))

from t2i.ImageResponse import ImageResponse


class ImageResponseTest(unittest.TestCase):
    """Test cases for ImageResponse."""

    def test_image_response_structure(self):
        """Test ImageResponse dataclass structure."""
        response = ImageResponse(
            image_type="url",
            image="https://example.com/image.png",
            revised_prompt="A revised prompt",
            raw={"test": "data"}
        )
        self.assertEqual(response.image_type, "url")
        self.assertEqual(response.image, "https://example.com/image.png")
        self.assertEqual(response.revised_prompt, "A revised prompt")
        self.assertEqual(response.raw, {"test": "data"})

    def test_image_response_with_binary(self):
        """Test ImageResponse with binary data."""
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 100
        response = ImageResponse(
            image_type="jpeg",
            image=jpeg_data,
            revised_prompt=None,
            raw=None
        )
        self.assertEqual(response.image_type, "jpeg")
        self.assertEqual(response.image, jpeg_data)
        self.assertIsNone(response.revised_prompt)


if __name__ == '__main__':
    unittest.main()

