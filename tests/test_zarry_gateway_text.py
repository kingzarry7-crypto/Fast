import unittest
from uuid import uuid4
from unittest.mock import Mock

from zarry_gateway.identity import AuthenticatedPrincipal
from zarry_gateway.providers import SelfHostedZarryProvider
from zarry_gateway.schemas import AssistantRequest
from zarry_gateway.service import AssistantService


class ProviderTests(unittest.TestCase):
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
