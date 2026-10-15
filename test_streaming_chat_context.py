"""Regression tests for context passed to the Colab-hosted Zarry model."""

import unittest

from streaming_chat import _build_zarry_context


class TestZarryStreamingContext(unittest.TestCase):
    def test_keeps_system_prompt_project_memory_and_recent_user_turns(self):
        messages = [
            {"role": "system", "content": "You are King Zarry AI. Project memory: use the real Railway backend."},
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
            {"role": "user", "content": "How should you use my project context?"},
        ]

        prompt, payload_messages = _build_zarry_context(messages)

        self.assertIn("You are King Zarry AI", prompt)
        self.assertIn("Project memory: use the real Railway backend", prompt)
        self.assertIn("USER: How should you use my project context?", prompt)
        self.assertEqual(payload_messages[0], messages[0])
        self.assertEqual(payload_messages[-1], messages[-1])

    def test_without_system_message_still_keeps_recent_chat(self):
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "latest"},
        ]

        prompt, payload_messages = _build_zarry_context(messages)

        self.assertIn("USER: latest", prompt)
        self.assertNotIn("SYSTEM INSTRUCTIONS", prompt)
        self.assertEqual(payload_messages, messages)


if __name__ == "__main__":
    unittest.main()
