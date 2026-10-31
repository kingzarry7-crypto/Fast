import unittest

from zarry_gateway.replicate_image import replicate_zimage_turbo_cost_usd


class ReplicateZImageTurboPricingTests(unittest.TestCase):
    def test_published_resolution_tiers_are_charged_exactly(self):
        self.assertEqual(replicate_zimage_turbo_cost_usd(512, 512), "0.0025")
        self.assertEqual(replicate_zimage_turbo_cost_usd(1024, 768), "0.005")
        self.assertEqual(replicate_zimage_turbo_cost_usd(1024, 1024), "0.01")

    def test_rejects_dimensions_outside_published_price_schedule(self):
        with self.assertRaises(ValueError):
            replicate_zimage_turbo_cost_usd(2048, 2048)
        with self.assertRaises(ValueError):
            replicate_zimage_turbo_cost_usd(0, 512)


if __name__ == "__main__":
    unittest.main()
