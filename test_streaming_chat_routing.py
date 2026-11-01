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
    def test_explicit_huggingface_is_primary_even_when_private_qwen_is_configured(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "HF",
            "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "",
        }, clear=True), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", "hf-test"), \
             patch.object(streaming_chat.ai_engine, "OPENAI_API_KEY", "openai-test"), \
             patch.object(streaming_chat, "_stream_openai_compatible", return_value=iter(["chunk"])):
            providers = [name for name, _stream in _provider_streams([])]

        self.assertEqual(providers[0], "huggingface")
        self.assertNotEqual(providers[0], "zarry")
        self.assertIn("openai", providers)

    def test_explicit_huggingface_is_not_selected_without_token(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "HF",
            "ZARRY_PRIVATE_SERVICE_URL": "",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "",
        }, clear=True), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", ""), \
             patch.object(streaming_chat.ai_engine, "OPENAI_API_KEY", "openai-test"):
            providers = [name for name, _stream in _provider_streams([])]

        self.assertNotIn("huggingface", providers)
        self.assertEqual(providers[0], "openai")

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

    def test_private_qwen_uses_openai_before_known_invalid_groq_fallback(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER": "AUTO",
            "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "",
        }, clear=True), \
             patch.object(streaming_chat.ai_engine, "HF_TOKEN", "hf-test"), \
             patch.object(streaming_chat.ai_engine, "CLOUDFLARE_AI_TOKEN", "cf-test"), \
             patch.object(streaming_chat.ai_engine, "OPENAI_API_KEY", "openai-test"), \
             patch.object(streaming_chat.ai_engine, "GEMINI_API_KEY", "gemini-test"), \
             patch.object(streaming_chat, "_GROQ_KEY", "groq-test"), \
             patch.object(streaming_chat, "_OPENROUTER_KEY", "router-test"), \
             patch.object(streaming_chat, "_CHUTES_KEY", "chutes-test"), \
             patch.object(streaming_chat, "_stream_zarry", return_value=iter(["qwen"])), \
             patch.object(streaming_chat, "_stream_openai_compatible", return_value=iter(["fallback"])), \
             patch.object(streaming_chat, "_stream_cloudflare", return_value=iter(["cloudflare"])):
            providers = [name for name, _stream in _provider_streams([])]

        self.assertEqual(providers[:3], ["zarry", "openai", "groq"])
        self.assertEqual(providers[-1], "huggingface")

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
        self.assertEqual(
            provider_class.return_value.generate.call_args.kwargs["timeout"],
            (2.0, 6.0),
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

    def test_auto_streaming_order_prefers_openai_before_groq_fallback(self):
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

        self.assertEqual(providers[:2], ["openai", "groq"])


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

    def test_exhausted_stream_providers_do_not_retry_qwen_through_ai_engine(self):
        engine = Mock()
        engine._load_memory_history.return_value = []
        engine._load_persistent_context.return_value = ""
        engine._build_openai_messages.return_value = [{"role": "user", "content": "how"}]

        def fail():
            raise TimeoutError("upstream timed out")
            yield "unreachable"

        with patch("streaming_chat.ai_engine.AIEngine", return_value=engine), \
             patch("streaming_chat.ai_engine._detect_media_intent", return_value=None), \
             patch("coding_request.handle_coding_request", return_value=None), \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", return_value=None), \
             patch("web_research_engine.should_research", return_value=False), \
             patch("tavily_search.should_trigger_tavily", return_value=False), \
             patch("streaming_chat._provider_streams", return_value=[("zarry", fail())]):
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="how",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        self.assertFalse(any(event.get("type") == "done" for event in events))
        self.assertTrue(any(event.get("type") == "error" for event in events))
        engine.ask.assert_not_called()

    def test_partial_stream_failure_is_terminal_and_does_not_try_second_provider(self):
        engine = Mock()
        engine._load_memory_history.return_value = []
        engine._load_persistent_context.return_value = ""
        engine._build_openai_messages.return_value = [{"role": "user", "content": "how"}]
        second_provider_started = []

        def partial_then_fail():
            yield "partial answer"
            raise TimeoutError("connection lost")

        def second_provider():
            second_provider_started.append(True)
            yield "duplicate answer"

        with patch("streaming_chat.ai_engine.AIEngine", return_value=engine), \
             patch("streaming_chat.ai_engine._detect_media_intent", return_value=None), \
             patch("coding_request.handle_coding_request", return_value=None), \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", return_value=None), \
             patch("web_research_engine.should_research", return_value=False), \
             patch("tavily_search.should_trigger_tavily", return_value=False), \
             patch("streaming_chat._provider_streams", return_value=[
                 ("zarry", partial_then_fail()),
                 ("openai", second_provider()),
             ]):
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="how",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        deltas = [event.get("text") for event in events if event.get("type") == "delta"]
        self.assertEqual(deltas, ["partial answer"])
        self.assertTrue(any(event.get("type") == "error" for event in events))
        self.assertFalse(any(event.get("type") == "done" for event in events))
        self.assertEqual(second_provider_started, [])
        engine.ask.assert_not_called()


    def test_stream_latency_logs_provider_first_delta_and_completion(self):
        engine = Mock()
        engine._load_memory_history.return_value = []
        engine._load_persistent_context.return_value = ""
        engine._build_openai_messages.return_value = [{"role": "user", "content": "how"}]

        with patch("streaming_chat.ai_engine.AIEngine", return_value=engine), \
             patch("streaming_chat.ai_engine._detect_media_intent", return_value=None), \
             patch("coding_request.handle_coding_request", return_value=None), \
             patch("account_agent.handle_web_request", return_value=None), \
             patch("agent_router.route_agent_request", return_value=None), \
             patch("web_research_engine.should_research", return_value=False), \
             patch("tavily_search.should_trigger_tavily", return_value=False), \
             patch("streaming_chat.ai_engine.clean_ai_response", side_effect=lambda value: value), \
             patch("streaming_chat._provider_streams", return_value=[("zarry", iter(["hello"]))]), \
             self.assertLogs("kz_streaming_chat", level="INFO") as captured:
            events = _events(_build_stream_generator(
                user_id="user-1",
                message="how",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        self.assertTrue(any(event.get("type") == "done" for event in events))
        output = "\n".join(captured.output)
        self.assertIn("ZARRY_STREAM_PROVIDER_START provider=zarry", output)
        self.assertIn("ZARRY_STREAM_FIRST_DELTA provider=zarry", output)
        self.assertIn("ZARRY_STREAM_PROVIDER_COMPLETE provider=zarry", output)
        self.assertIn("first_delta_ms=", output)
        self.assertIn("total_elapsed_ms=", output)


if __name__ == "__main__":
    unittest.main()


class StreamingTimeoutBudgetTests(unittest.TestCase):
    def test_stream_timeout_defaults_to_a_bounded_8_second_read(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(streaming_chat._bounded_stream_timeout(), 8)

    def test_stream_timeout_rejects_invalid_and_clamps_extreme_values(self):
        with patch.dict(os.environ, {"AI_STREAM_TIMEOUT": "not-a-number"}, clear=True):
            self.assertEqual(streaming_chat._bounded_stream_timeout(), 8)
        with patch.dict(os.environ, {"AI_STREAM_TIMEOUT": "999"}, clear=True):
            self.assertEqual(streaming_chat._bounded_stream_timeout(), 10)
        with patch.dict(os.environ, {"AI_STREAM_TIMEOUT": "1"}, clear=True):
            self.assertEqual(streaming_chat._bounded_stream_timeout(), 5)

    def test_private_qwen_wait_defaults_to_six_seconds(self):
        messages = [{"role": "user", "content": "Hello"}]
        with patch.dict(os.environ, {
            "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
            "ZARRY_SERVICE_URL": "",
            "ZARRY_API_URL": "",
        }, clear=True), patch(
            "zarry_gateway.providers.SelfHostedZarryProvider"
        ) as provider_class:
            provider_class.return_value.generate.return_value = "Qwen response"
            list(streaming_chat._stream_zarry(messages))
        self.assertEqual(
            provider_class.return_value.generate.call_args.kwargs["timeout"],
            (2.0, 6.0),
        )


class StreamingThinkSanitizationTests(unittest.TestCase):
    def test_think_blocks_are_never_emitted_even_when_tags_cross_chunks(self):
        sanitizer = streaming_chat._ThinkTagFilter()
        visible = [
            sanitizer.feed("Hello <thi"),
            sanitizer.feed("nk>private reasoning</th"),
            sanitizer.feed("ink> world"),
            sanitizer.finish(),
        ]
        self.assertEqual("".join(visible), "Hello  world")
        self.assertNotIn("private reasoning", "".join(visible))

    def test_unterminated_think_block_is_discarded_at_end_of_stream(self):
        sanitizer = streaming_chat._ThinkTagFilter()
        visible = sanitizer.feed("Visible answer<think>unfinished private reasoning")
        visible += sanitizer.finish()
        self.assertEqual(visible, "Visible answer")
        self.assertNotIn("unfinished private reasoning", visible)

    def test_incomplete_tag_prefix_is_flushed_as_ordinary_text(self):
        sanitizer = streaming_chat._ThinkTagFilter()
        visible = sanitizer.feed("Hello <th") + sanitizer.finish()
        self.assertEqual(visible, "Hello <th")

    def test_stream_generator_never_emits_think_content_in_sse_deltas(self):
        engine = Mock()
        engine._load_memory_history.return_value = []
        engine._load_persistent_context.return_value = ""
        engine._build_openai_messages.return_value = [{"role": "user", "content": "Hi"}]
        cleaner = streaming_chat.ai_engine.clean_ai_response

        with (
            patch("streaming_chat.ai_engine.AIEngine", return_value=engine),
            patch("streaming_chat.ai_engine._detect_media_intent", return_value=None),
            patch("coding_request.handle_coding_request", return_value=None),
            patch("account_agent.handle_web_request", return_value=None),
            patch("agent_router.route_agent_request", return_value=None),
            patch("web_research_engine.should_research", return_value=False),
            patch("tavily_search.should_trigger_tavily", return_value=False),
            patch("streaming_chat.ai_engine.clean_ai_response", side_effect=cleaner),
            patch("streaming_chat._provider_streams", return_value=[(
                "zarry",
                iter(["Hello <thi", "nk>private reasoning</th", "ink> world"]),
            )]),
        ):
            events = _events(streaming_chat._build_stream_generator(
                user_id="user-1",
                message="Hi",
                conversation_id="conversation-1",
                memory_factory=lambda *_: _Memory(),
            ))

        deltas = "".join(
            event.get("text", "") for event in events if event.get("type") == "delta"
        )
        self.assertEqual(deltas, "Hello  world")
        self.assertNotIn("private reasoning", deltas)
        self.assertTrue(any(event.get("type") == "done" for event in events))
