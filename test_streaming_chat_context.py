"""Regression tests for context passed to the Colab-hosted Zarry model."""

from streaming_chat import _build_zarry_context


def test_zarry_context_keeps_system_prompt_and_recent_user_turns():
    messages = [
        {"role": "system", "content": "You are King Zarry AI. Project memory: use the real Railway backend."},
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
        {"role": "user", "content": "How should you use my project context?"},
    ]

    prompt, payload_messages = _build_zarry_context(messages)

    assert "You are King Zarry AI" in prompt
    assert "Project memory: use the real Railway backend" in prompt
    assert "USER: How should you use my project context?" in prompt
    assert payload_messages[0] == messages[0]
    assert payload_messages[-1] == messages[-1]


def test_zarry_context_without_system_message_still_keeps_recent_chat():
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "latest"},
    ]

    prompt, payload_messages = _build_zarry_context(messages)

    assert "USER: latest" in prompt
    assert "SYSTEM INSTRUCTIONS" not in prompt
    assert payload_messages == messages
