import unittest
from uuid import uuid4

from zarry_gateway.identity import AuthenticatedPrincipal
from zarry_gateway.schemas import ImageRequest
from zarry_gateway.service import AssistantService


class RecordingImageProvider:
    def __init__(self):
        self.calls = []

    def generate(self, prompt, *, request_id, size):
        self.calls.append((prompt, request_id, size))
        return {
            "request_id": request_id,
            "image_url": "https://images.example/generated.png",
            "provider": "test-provider",
            "fallback_used": False,
            "budget_reserved_usd": "0.01",
        }


class AssistantImageServiceTests(unittest.TestCase):
    def test_service_passes_validated_size_to_provider_and_returns_public_contract(self):
        provider = RecordingImageProvider()
        service = AssistantService(image_provider=provider)
        request_id = uuid4()
        principal = AuthenticatedPrincipal(
            subject_id="web:user-1", platform="web", platform_user_id="user-1"
        )
        response = service.image(
            principal=principal,
            payload=ImageRequest(prompt="A lighthouse at sunset", size="1024x768", request_id=request_id),
        )
        self.assertEqual(provider.calls, [("A lighthouse at sunset", request_id, "1024x768")])
        self.assertEqual(response, {
            "request_id": request_id,
            "image_url": "https://images.example/generated.png",
            "provider": "test-provider",
            "fallback_used": False,
        })


if __name__ == "__main__":
    unittest.main()
