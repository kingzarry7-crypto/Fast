import unittest
from uuid import uuid4
from unittest.mock import Mock, patch

from zarry_gateway.identity import AuthenticatedPrincipal
from zarry_gateway.providers import SelfHostedZarryProvider
from zarry_gateway.schemas import AssistantRequest
from zarry_gateway.service import AssistantService


class ProviderTests(unittest.TestCase):
    def test_defaults_known_railway_public_zarry_url_to_private_service_endpoint(self):
        with patch.dict(
            "os.environ",
            {
                "ZARRY_SERVICE_URL": "https://zarry-production.up.railway.app",
                "ZARRY_API_KEY": "secret",
            },
            clear=True,
        ):
            provider = SelfHostedZarryProvider()
        self.assertEqual(provider.base_url, "http://zarry.railway.internal:8080")

    def test_explicit_private_service_url_overrides_public_url(self):
        with patch.dict(
            "os.environ",
            {
                "ZARRY_SERVICE_URL": "https://zarry-production.up.railway.app",
                "ZARRY_PRIVATE_SERVICE_URL": "http://zarry.railway.internal:8080",
                "ZARRY_API_KEY": "secret",
            },
            clear=True,
        ):
            provider = SelfHostedZarryProvider()
        self.assertEqual(provider.base_url, "http://zarry.railway.internal:8080")

    def test_calls_dedicated_chat_endpoint_and_checks_request_id(self):
        request_id = uuid4()
        response = Mock()
        response.json.return_value = {"request_id": str(request_id), "response": "Hello"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        provider = SelfHostedZarryProvider("https://zarry.example", "secret", session=session)
        result = provider.generate(message="Hi", request_id=request_id)
        self.assertEqual(result, "Hello")
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], "https://zarry.example/v1/chat")
        self.assertEqual(kwargs["json"]["request_id"], str(request_id))
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "user")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")

    def test_internal_system_context_is_folded_into_first_user_message(self):
        request_id = uuid4()
        response = Mock()
        response.json.return_value = {"request_id": str(request_id), "response": "Hello"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        provider = SelfHostedZarryProvider(
            "http://zarry.railway.internal:8080", "secret", session=session
        )
        provider.generate(
            message="Hello",
            request_id=request_id,
            messages=[
                {"role": "system", "content": "Use the user's saved context."},
                {"role": "user", "content": "Hello"},
            ],
        )
        sent = session.post.call_args.kwargs["json"]["messages"]
        self.assertEqual([item["role"] for item in sent], ["user"])
        self.assertIn("Use the user's saved context.", sent[0]["content"])
        self.assertTrue(sent[0]["content"].endswith("Hello"))

    def test_allows_railway_private_http_and_uses_cpu_safe_timeout(self):
        request_id = uuid4()
        response = Mock()
        response.json.return_value = {"request_id": str(request_id), "response": "Hello"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        provider = SelfHostedZarryProvider(
            "http://zarry.railway.internal:8080", "secret", session=session
        )
        self.assertEqual(provider.generate(message="Hi", request_id=request_id), "Hello")
        kwargs = session.post.call_args.kwargs
        self.assertEqual(kwargs["timeout"], (5.0, 180.0))
        self.assertEqual(session.post.call_args.args[0], "http://zarry.railway.internal:8080/v1/chat")

    def test_refuses_http_or_missing_credentials(self):
        provider = SelfHostedZarryProvider("http://zarry.example", "secret")
        with self.assertRaises(RuntimeError):
            provider.generate(message="Hi", request_id=uuid4())

    def test_rejects_mismatched_request_id(self):
        response = Mock()
        response.json.return_value = {"request_id": "wrong-id", "response": "Hello"}
        response.raise_for_status.return_value = None
        session = Mock()
        session.post.return_value = response
        provider = SelfHostedZarryProvider("https://zarry.example", "secret", session=session)
        with self.assertRaises(RuntimeError):
            provider.generate(message="Hi", request_id=uuid4())


class AssistantServiceTests(unittest.TestCase):
    def test_returns_provider_attribution_and_never_claims_fallback(self):
        provider = Mock()
        provider.name = "self-hosted-zarry"
        provider.generate.return_value = "Hello from ZARRY"
        service = AssistantService(provider)
        principal = AuthenticatedPrincipal("web:user-1", "web", "user-1")
        payload = AssistantRequest(message="Hello")
        result = service.chat(principal=principal, payload=payload)
        self.assertEqual(result["response"], "Hello from ZARRY")
        self.assertEqual(result["provider"], "self-hosted-zarry")
        self.assertFalse(result["fallback_used"])

    def test_provider_failure_propagates_without_unapproved_fallback(self):
        provider = Mock()
        provider.name = "self-hosted-zarry"
        provider.generate.side_effect = TimeoutError("provider timeout")
        service = AssistantService(provider)
        principal = AuthenticatedPrincipal("web:user-1", "web", "user-1")
        with self.assertRaises(TimeoutError):
            service.chat(principal=principal, payload=AssistantRequest(message="Hello"))


if __name__ == "__main__":
    unittest.main()
