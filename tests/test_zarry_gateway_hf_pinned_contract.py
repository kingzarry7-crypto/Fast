"""Regression tests for the pinned HF image billing contract."""
import unittest
from uuid import uuid4

from zarry_gateway.image import (
    HF_ZIMAGE_MODEL,
    HuggingFaceImageProvider,
    fal_zimage_turbo_reservation_usd,
    fal_zimage_turbo_settlement_usd,
)


class Ledger:
    def __init__(self):
        self.calls = []

    def reserve(self, request_id, amount):
        self.calls.append(("reserve", amount))

    def settle(self, request_id, amount):
        self.calls.append(("settle", amount))


class Storage:
    def save(self, image, request_id):
        return "https://images.example/image.png"


class Client:
    def __init__(self):
        self.calls = []

    def text_to_image(self, **kwargs):
        self.calls.append(kwargs)
        return type("Image", (), {"size": (1024, 768)})()


class PinnedProviderContractTests(unittest.TestCase):
    def make_provider(self, *, model=HF_ZIMAGE_MODEL, provider="fal-ai"):
        self.ledger = Ledger()
        self.client = Client()
        return HuggingFaceImageProvider(
            api_key="hf_test_token",
            model=model,
            provider=provider,
            ledger=self.ledger,
            cost_estimator=fal_zimage_turbo_reservation_usd,
            actual_cost_resolver=fal_zimage_turbo_settlement_usd,
            storage=Storage(),
            client_factory=lambda **kwargs: self.client,
        )

    def test_only_pinned_model_and_fal_provider_are_configured(self):
        self.assertTrue(self.make_provider().is_configured())
        self.assertFalse(self.make_provider(model="another/model").is_configured())
        self.assertFalse(self.make_provider(provider="automatic").is_configured())

    def test_unpinned_model_is_rejected_before_reservation_or_dispatch(self):
        provider = self.make_provider(model="another/model")
        with self.assertRaisesRegex(RuntimeError, "pinned model/provider"):
            provider.generate("a lighthouse", request_id=uuid4(), size="1024x768")
        self.assertEqual(self.ledger.calls, [])
        self.assertEqual(self.client.calls, [])

    def test_unpinned_provider_is_rejected_before_reservation_or_dispatch(self):
        provider = self.make_provider(provider="automatic")
        with self.assertRaisesRegex(RuntimeError, "pinned model/provider"):
            provider.generate("a lighthouse", request_id=uuid4(), size="1024x768")
        self.assertEqual(self.ledger.calls, [])
        self.assertEqual(self.client.calls, [])


if __name__ == "__main__":
    unittest.main()
