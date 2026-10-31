import unittest

from zarry_gateway.replicate_image import ReplicateZImageTurboProvider, replicate_zimage_turbo_cost_usd


class ReplicateZImageTurboPricingTests(unittest.TestCase):
    def test_published_resolution_tiers_are_charged_exactly(self):
        self.assertEqual(replicate_zimage_turbo_cost_usd(512, 512), "0.0025")
        self.assertEqual(replicate_zimage_turbo_cost_usd(1024, 768), "0.005")
        self.assertEqual(replicate_zimage_turbo_cost_usd(1024, 1024), "0.01")

    def test_missing_direct_provider_credentials_fail_before_reserving(self):
        class Ledger:
            def __init__(self):
                self.calls = []
            def reserve(self, *args):
                self.calls.append(args)
        ledger = Ledger()
        provider = ReplicateZImageTurboProvider(
            api_token="", model_version="", ledger=ledger, storage=object(),
            session=object(),
        )
        with self.assertRaisesRegex(RuntimeError, "Replicate token and pinned"):
            provider.generate("a lighthouse", request_id="request-1", width=512, height=512)
        self.assertEqual(ledger.calls, [])

    def test_rejects_mutable_model_alias_before_reserving(self):
        class Ledger:
            def __init__(self):
                self.calls = []
            def reserve(self, *args):
                self.calls.append(args)
        ledger = Ledger()
        provider = ReplicateZImageTurboProvider(
            api_token="replicate-token", model_version="latest",
            ledger=ledger, storage=object(), session=object(),
        )
        with self.assertRaisesRegex(RuntimeError, "immutable 64-character"):
            provider.generate("a lighthouse", request_id="request-2", width=512, height=512)
        self.assertEqual(ledger.calls, [])

    def test_rejects_dimensions_outside_published_price_schedule(self):
        with self.assertRaises(ValueError):
            replicate_zimage_turbo_cost_usd(2048, 2048)
        with self.assertRaises(ValueError):
            replicate_zimage_turbo_cost_usd(0, 512)


if __name__ == "__main__":
    unittest.main()
