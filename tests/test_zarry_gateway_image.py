import unittest
from uuid import uuid4

from zarry_gateway.image import HF_ZIMAGE_MODEL, HuggingFaceImageProvider


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
            api_key="hf_secret", model=HF_ZIMAGE_MODEL, provider="fal-ai", ledger=ledger,
            cost_estimator=lambda model, size: "0.01",
            actual_cost_resolver=lambda image, model, size: "0.008",
            client_factory=lambda **kwargs: client, storage=storage,
        )
        request_id = uuid4()
        result = provider.generate("a red kite", request_id=request_id, size="1024x1024")
        self.assertEqual(result["image_url"], "https://images.example/generated.png")
        self.assertEqual([c[0] for c in ledger.calls], ["reserve", "settle"])
        self.assertEqual(client.calls[0]["prompt"], "a red kite")
        self.assertEqual(client.calls[0]["provider"], "fal-ai")
        self.assertEqual(client.calls[0]["width"], 1024)
        self.assertEqual(client.calls[0]["height"], 1024)
        self.assertEqual(storage.saved[0][1], request_id)

    def test_unknown_cost_fails_before_provider_dispatch(self):
        ledger, client = FakeLedger(), FakeClient()
        provider = HuggingFaceImageProvider(
            api_key="hf_secret", model=HF_ZIMAGE_MODEL, provider="fal-ai", ledger=ledger,
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
            api_key="hf_secret", model=HF_ZIMAGE_MODEL, provider="fal-ai", ledger=ledger,
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
            api_key="hf_secret", model=HF_ZIMAGE_MODEL, provider="fal-ai", ledger=ledger,
            cost_estimator=lambda model, size: "0.01",
            actual_cost_resolver=lambda image, model, size: "0.01",
            client_factory=lambda **kwargs: BrokenClient(), storage=FakeStorage(),
        )
        with self.assertRaises(TimeoutError):
            provider.generate("test", request_id=uuid4(), size="1024x1024")
        self.assertEqual([c[0] for c in ledger.calls], ["reserve"])


class HuggingFaceFirstImageProviderTests(unittest.TestCase):
    def test_fal_z_image_turbo_price_rounds_up_to_billable_megapixels(self):
        from zarry_gateway.image import fal_zimage_turbo_cost_usd
        self.assertEqual(fal_zimage_turbo_cost_usd("Tongyi-MAI/Z-Image-Turbo", "1024x768"), "0.005")
        self.assertEqual(fal_zimage_turbo_cost_usd("Tongyi-MAI/Z-Image-Turbo", "1024x1024"), "0.01")
        from zarry_gateway.image import fal_zimage_turbo_reservation_usd
        self.assertEqual(fal_zimage_turbo_reservation_usd("Tongyi-MAI/Z-Image-Turbo", "1024x768"), "0.01")

    def test_huggingface_primary_is_used_when_configured(self):
        from zarry_gateway.image import HuggingFaceFirstImageProvider
        class Primary:
            def __init__(self): self.calls = []
            def is_configured(self): return True
            def generate(self, prompt, *, request_id, size):
                self.calls.append((prompt, request_id, size))
                return {"request_id": request_id, "image_url": "https://images.example/hf.png",
                        "provider": "huggingface-fal-z-image-turbo", "fallback_used": False}
        class Fallback:
            def generate(self, *args, **kwargs): raise AssertionError("fallback must not run")
        primary = Primary()
        provider = HuggingFaceFirstImageProvider(primary, Fallback())
        request_id = uuid4()
        result = provider.generate("a red kite", request_id=request_id, width=1024, height=768)
        self.assertEqual(result["provider"], "huggingface-fal-z-image-turbo")
        self.assertEqual(primary.calls, [("a red kite", request_id, "1024x768")])

    def test_replicate_is_used_only_when_huggingface_is_unconfigured_before_dispatch(self):
        from zarry_gateway.image import HuggingFaceFirstImageProvider
        class Primary:
            def is_configured(self): return False
            def generate(self, *args, **kwargs): raise AssertionError("unconfigured primary must not run")
        class Fallback:
            def generate(self, prompt, *, request_id, width, height):
                return {"request_id": request_id, "image_url": "https://images.example/replicate.png",
                        "provider": "replicate-z-image-turbo", "fallback_used": False}
        provider = HuggingFaceFirstImageProvider(Primary(), Fallback())
        result = provider.generate("a red kite", request_id=uuid4(), width=1024, height=1024)
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["provider"], "replicate-z-image-turbo")

    def test_ambiguous_huggingface_failure_never_dispatches_replicate_fallback(self):
        from zarry_gateway.image import HuggingFaceFirstImageProvider
        class Primary:
            def is_configured(self): return True
            def generate(self, *args, **kwargs): raise TimeoutError("unknown provider outcome")
        class Fallback:
            def __init__(self): self.calls = []
            def generate(self, *args, **kwargs): self.calls.append((args, kwargs))
        fallback = Fallback()
        provider = HuggingFaceFirstImageProvider(Primary(), fallback)
        with self.assertRaises(TimeoutError):
            provider.generate("a red kite", request_id=uuid4(), width=1024, height=1024)
        self.assertEqual(fallback.calls, [])


    def test_incomplete_huggingface_cost_contract_blocks_replicate_fallback(self):
        from zarry_gateway.image import HuggingFaceFirstImageProvider
        class Primary:
            api_key = "configured-token"
            def is_configured(self): return False
        class Fallback:
            def __init__(self): self.calls = []
            def generate(self, *args, **kwargs): self.calls.append((args, kwargs))
        fallback = Fallback()
        provider = HuggingFaceFirstImageProvider(Primary(), fallback)
        with self.assertRaisesRegex(RuntimeError, "billing or storage contract is incomplete"):
            provider.generate("a red kite", request_id=uuid4(), width=1024, height=1024)
        self.assertEqual(fallback.calls, [])


    def test_huggingface_settlement_uses_returned_dimensions(self):
        from zarry_gateway.image import fal_zimage_turbo_settlement_usd
        class GeneratedImage:
            size = (1024, 768)
        self.assertEqual(
            fal_zimage_turbo_settlement_usd(
                GeneratedImage(), "Tongyi-MAI/Z-Image-Turbo", "1024x768"
            ),
            "0.005",
        )


    def test_service_hides_internal_budget_metadata_from_strict_image_response(self):
        from zarry_gateway.identity import AuthenticatedPrincipal
        from zarry_gateway.schemas import ImageRequest
        from zarry_gateway.service import AssistantService

        class Provider:
            def __init__(self): self.received = None
            def generate(self, prompt, *, request_id, width, height):
                self.received = (prompt, request_id, width, height)
                return {
                    "request_id": request_id,
                    "image_url": "https://images.example/generated.png",
                    "provider": "huggingface-fal-z-image-turbo",
                    "fallback_used": False,
                    "budget_reserved_usd": "0.01",
                }

        provider = Provider()
        service = AssistantService(image_provider=provider)
        principal = AuthenticatedPrincipal(
            subject_id="web:user-1", platform="web", platform_user_id="user-1"
        )
        payload = ImageRequest(prompt="a lighthouse", size="1024x768")
        result = service.image(principal=principal, payload=payload)
        self.assertEqual(set(result), {
            "request_id", "image_url", "provider", "fallback_used"
        })
        self.assertEqual(provider.received, ("a lighthouse", payload.request_id, 1024, 768))


if __name__ == "__main__":
    unittest.main()
