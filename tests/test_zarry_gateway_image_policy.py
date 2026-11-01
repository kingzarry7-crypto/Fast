import unittest
from unittest.mock import patch

from zarry_gateway.policy import image_generation_enabled


class ImageGenerationPolicyTests(unittest.TestCase):
    def test_image_generation_defaults_off(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(image_generation_enabled())

    def test_legacy_enable_flag_alone_cannot_enable_generation(self):
        with patch.dict("os.environ", {
            "ZARRY_IMAGE_ENABLED": "true",
            "ZARRY_IMAGE_LIVE_SMOKE_APPROVED": "false",
        }, clear=True):
            self.assertFalse(image_generation_enabled())

    def test_live_smoke_approval_alone_cannot_enable_generation(self):
        with patch.dict("os.environ", {
            "ZARRY_IMAGE_ENABLED": "false",
            "ZARRY_IMAGE_LIVE_SMOKE_APPROVED": "true",
        }, clear=True):
            self.assertFalse(image_generation_enabled())

    def test_both_explicit_gates_are_required(self):
        with patch.dict("os.environ", {
            "ZARRY_IMAGE_ENABLED": "true",
            "ZARRY_IMAGE_LIVE_SMOKE_APPROVED": "true",
        }, clear=True):
            self.assertTrue(image_generation_enabled())


if __name__ == "__main__":
    unittest.main()
