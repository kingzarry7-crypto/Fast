"""Regression tests ensuring streaming chat uses specialist intent routing."""

import json
import os
import unittest
from unittest.mock import Mock, patch

import coding_request

import streaming_chat
from streaming_chat import _build_stream_generator, _provider_streams


class _Memory:
    def add_message(self, *args, **kwargs):
        return None


def _events(chunks):
    parsed = []
    for chunk in chunks:
        for line in str(chunk).splitlines():
            if line.startswith("data: "):
                parsed.append(json.loads(line[6:]))
    return parsed


class StreamingProviderPreferenceTests(unittest.TestCase):
    def test_explicit_ai_provider_is_first_in_streaming_fallback_order(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "openrouter", "ZARRY_API_URL": ""}, clear=False), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", "hf-test"), \
             patch.object(streaming_chat.ai_engine, "CLOUDFLARE_AI_TOKEN", "cf-test"), \
             patch.object(streaming_chat.ai_engine, "OPENAI_API_KEY", "openai-test"), \
             patch.object(streaming_chat, "_GROQ_KEY", "groq-test"), \
             patch.object(streaming_chat, "_OPENROUTER_KEY", "router-test"), \
             patch.object(streaming_chat, "_CHUTES_KEY", "chutes-test"), \
             patch.object(streaming_chat, "_stream_openai_compatible", return_value=iter(["chunk"])), \
             patch.object(streaming_chat, "_stream_cloudflare", return_value=iter(["chunk"])), \
             patch.object(streaming_chat, "_stream_zarry", return_value=iter(["chunk"])):
            providers = [name for name, _stream in _provider_streams([])]

        self.assertEqual(providers[0], "openrouter")
        self.assertIn("openai", providers)
        self.assertIn("groq", providers)
        self.assertIn("chutes", providers)

    def test_private_qwen_service_is_primary_without_legacy_zarry_api_url(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "AUTO",
            "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "",
        }, clear=True), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", ""), \
             patch.object(streaming_chat, "_stream_zarry", return_value=iter(["qwen reply"])):
            providers = [name for name, _stream in _provider_streams([])]

        self.assertEqual(providers[0], "zarry")

    def test_private_qwen_stream_calls_v1_chat_even_when_legacy_url_exists(self):
        messages = [
            {"role": "system", "content": "Keep answers grounded."},
            {"role": "user", "content": "Hello"},
        ]
        with patch.dict(os.environ, {
            "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "https://legacy.example/generate",
        }, clear=False), patch(
            "zarry_gateway.providers.SelfHostedZarryProvider"
        ) as provider_class:
            provider_class.return_value.generate.return_value = "Qwen response"
            chunks = list(streaming_chat._stream_zarry(messages))

        self.assertEqual(chunks, ["Qwen response"])
        provider_class.return_value.generate.assert_called_once()
        self.assertEqual(
            provider_class.return_value.generate.call_args.kwargs["messages"],
            messages,
        )

    def test_ai_engine_uses_private_qwen_for_normal_chat(self):
        engine = streaming_chat.ai_engine.AIEngine()
        provider = Mock()
        provider.generate.return_value = "Qwen answer"
        with patch.dict(os.environ, {
            "AI_PROVIDER": "AUTO",
            "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "",
        }, clear=True), patch(
            "zarry_gateway.providers.SelfHostedZarryProvider", return_value=provider
        ) as provider_class:
            self.assertEqual(engine._get_provider_order()[0], "zarry")
            result = engine._call_providers_once("Hello", [], None, "", casual=True)

        self.assertEqual(result, "Qwen answer")
        provider_class.assert_called_once_with()
        provider.generate.assert_called_once()
        self.assertEqual(provider.generate.call_args.kwargs["message"], "Hello")

    def test_gemini_is_available_in_streaming_provider_order(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "GEMINI", "ZARRY_API_URL": ""}, clear=False), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", ""), \
             patch.object(streaming_chat.ai_engine, "GEMINI_API_KEY", "gemini-test-key"):
            providers = [name for name, _stream in _provider_streams([])]
        self.assertEqual(providers[0], "gemini")

    def test_auto_streaming_order_starts_with_cloudflare_when_zarry_and_hf_unset(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "AUTO", "ZARRY_API_URL": ""}, clear=False), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", ""), \
             patch.object(streaming_chat.ai_engine, "CLOUDFLARE_AI_TOKEN", "cf-test"), \
             patch.object(streaming_chat.ai_engine, "OPENAI_API_KEY", "openai-test"), \
             patch.object(streaming_chat, "_GROQ_KEY", "groq-test"), \
             patch.object(streaming_chat, "_OPENROUTER_KEY", "router-test"), \
             patch.object(streaming_chat, "_CHUTES_KEY", "chutes-test"), \
             patch.object(streaming_chat, "_stream_openai_compatible", return_value=iter(["chunk"])), \
             patch.object(streaming_chat, "_stream_cloudflare", return_value=iter(["chunk"])):
            providers = [name for name, _stream in _provider_streams([])]

        self.assertEqual(providers[0], "cloudflare")


class StreamingIntentRoutingTests(unittest.TestCase):
    def test_media_request_routes_before_coding_and_connector_agents(self):
        with patch("ai_engine.AIEngine._route_media_request", return_value="Please attach the image you want edited."), \
             patch("ai_engine.AIEngine._save_memory", return_value=None), \
             patch("coding_request.handle_coding_request") as coding, \
             patch("account_agent.handle_web_request") as connector:
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="Edit this picture of my gold chart",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        self.assertTrue(any(e.get("provider") == "media_agent" for e in events))
        self.assertTrue(any("attach the image" in e.get("text", "").lower() for e in events))
        coding.assert_not_called()
        connector.assert_not_called()

    def test_market_request_uses_specialist_agent_in_streaming_path(self):
        specialist = {
            "status": "completed",
            "provider": "market_agent",
            "operation": "analyze_market",
            "target": "XAU/USD",
            "reply": "Market Agent report — XAU/USD (1h). Signal: WAIT. No trade was placed.",
        }
        with patch("ai_engine.AIEngine._save_memory", return_value=None), \
             patch("coding_request.handle_coding_request", wraps=coding_request.handle_coding_request) as coding, \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", return_value=specialist):
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="Analyze gold on the 1h timeframe",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        self.assertTrue(any(e.get("provider") == "market_agent" for e in events))
        self.assertTrue(any("XAU/USD" in e.get("text", "") for e in events))
        # Use the real coding detector: a market-only request must be declined
        # so the specialist router can own the response.
        coding.assert_called_once_with("Analyze gold on the 1h timeframe")

    def test_market_router_failure_is_not_replaced_with_generic_guess(self):
        with patch("ai_engine.AIEngine._save_memory", return_value=None), \
             patch("coding_request.handle_coding_request", return_value=None), \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", side_effect=RuntimeError("provider failure")):
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="Give me a BTC signal",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        done = [e for e in events if e.get("type") == "done"]
        self.assertTrue(done)
        self.assertEqual(done[-1].get("status"), "unavailable")
        self.assertIn("No price or signal was invented", done[-1].get("text", ""))


if __name__ == "__main__":
    unittest.main()
