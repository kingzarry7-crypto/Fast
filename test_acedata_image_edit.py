import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ai_engine


class AceDataImageEditTests(unittest.TestCase):
    def test_edit_request_uses_edit_action_and_context_model(self):
        response = SimpleNamespace(
            status_code=200,
            json=lambda: {
                "success": True,
                "data": [{"image_url": "https://images.example/edited.png"}],
            },
        )
        with (
            patch.object(ai_engine, "ACEDATA_API_KEY", "test-token"),
            patch.object(ai_engine, "ACEDATA_IMAGE_MODEL", "flux-kontext-pro"),
            patch.object(ai_engine.requests, "post", return_value=response) as post,
        ):
            result = ai_engine.acedata_edit_image(
                prompt="Replace the background with a sunset beach",
                image_url="https://images.example/source.png",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://images.example/edited.png")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["action"], "edit")
        self.assertEqual(payload["model"], "flux-kontext-pro")
        self.assertEqual(payload["image_url"], "https://images.example/source.png")


if __name__ == "__main__":
    unittest.main()
