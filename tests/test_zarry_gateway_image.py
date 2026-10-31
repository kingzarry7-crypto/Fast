import unittest
from uuid import uuid4

from zarry_gateway.image import HuggingFaceImageProvider


class FakeLedger:
    def __init__(self):
        self.calls = []
    def reserve(self, request_id, estimate):
        self.calls.append(("reserve", request_id, estimate))
    def settle(self, request_id, actual):
        self.calls.append(("settle", request_id, actual))
    def release(self, request_id):
        self.calls.append(("release", request_id))


class FakeClient:
    def __init__(self, image=None):
        self.image = image or object()
        self.calls = []
    def text_to_image(self, **kwargs):
        self.calls.append(kwargs)
        return self.image


class FakeStorage:
    def __init__(self):
        self.saved = []
    def save(self, image, request_id):
        self.saved.append((image, request_id))
        return "https://images.example/generated.png"


class ImageProviderTests(unittest.TestCase):
    def test_reserves_before_dispatch_then_settles_and_stores(self):
        ledger, client, storage = FakeLedger(), FakeClient(), FakeStorage()
        provider = HuggingFaceImageProvider(
            api_key="hf_secret", model="test/model", ledger=ledger,
            cost_estimator=lambda model, size: "0.01",
            actual_cost_resolver=lambda image, model, size: "0.008",
            client_factory=lambda **kwargs: client, storage=storage,
        )
        request_id = uuid4()
        result = provider.generate("a red kite", request_id=request_id, size="1024x1024")
        self.assertEqual(result["image_url"], "https://images.example/generated.png")
        self.assertEqual([c[0] for c in ledger.calls], ["reserve", "settle"])
        self.assertEqual(client.calls[0]["prompt"], "a red kite")
        self.assertEqual(storage.saved[0][1], request_id)

    def test_unknown_cost_fails_before_provider_dispatch(self):
        ledger, client = FakeLedger(), FakeClient()
        provider = HuggingFaceImageProvider(
            api_key="hf_secret", model="test/model", ledger=ledger,
            cost_estimator=lambda model, size: None,
            actual_cost_resolver=lambda image, model, size: "0.01",
            client_factory=lambda **kwargs: client, storage=FakeStorage(),
        )
        with self.assertRaises(RuntimeError):
            provider.generate("test", request_id=uuid4(), size="1024x1024")
        self.assertEqual(client.calls, [])
        self.assertEqual(ledger.calls, [])

    def test_missing_actual_cost_keeps_reservation_and_does_not_store(self):
        ledger, client, storage = FakeLedger(), FakeClient(), FakeStorage()
        provider = HuggingFaceImageProvider(
            api_key="hf_secret", model="test/model", ledger=ledger,
            cost_estimator=lambda model, size: "0.01",
            actual_cost_resolver=lambda image, model, size: None,
            client_factory=lambda **kwargs: client, storage=storage,
        )
        with self.assertRaises(RuntimeError):
            provider.generate("test", request_id=uuid4(), size="1024x1024")
        self.assertEqual([c[0] for c in ledger.calls], ["reserve"])
        self.assertEqual(storage.saved, [])

    def test_ambiguous_provider_failure_keeps_reservation(self):
        ledger = FakeLedger()
        class BrokenClient:
            def text_to_image(self, **kwargs):
                raise TimeoutError("provider outcome is unknown")
        provider = HuggingFaceImageProvider(
            api_key="hf_secret", model="test/model", ledger=ledger,
            cost_estimator=lambda model, size: "0.01",
            actual_cost_resolver=lambda image, model, size: "0.01",
            client_factory=lambda **kwargs: BrokenClient(), storage=FakeStorage(),
        )
        with self.assertRaises(TimeoutError):
            provider.generate("test", request_id=uuid4(), size="1024x1024")
        self.assertEqual([c[0] for c in ledger.calls], ["reserve"])


if __name__ == "__main__":
    unittest.main()
