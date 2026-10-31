import unittest
from zarry_gateway.identity import IdentityResolver
class GatewayIdentityTests(unittest.TestCase):
    def test_platform_ids_are_isolated(self):
        resolver=IdentityResolver(); subjects={resolver.resolve(p,"123").subject_id for p in ("web","telegram","discord")}
        self.assertEqual(subjects, {"web:123","telegram:123","discord:123"})
    def test_names_are_not_identity_inputs(self):
        resolver=IdentityResolver(); self.assertNotEqual(resolver.resolve("telegram","1001").subject_id,resolver.resolve("discord","2002").subject_id)
    def test_only_explicit_verified_lookup_links(self):
        resolver=IdentityResolver(verified_link_lookup=lambda platform, external_id: "account-7")
        self.assertEqual(resolver.resolve("telegram","1").subject_id,resolver.resolve("discord","2").subject_id)
    def test_invalid_platform_or_id_rejected(self):
        resolver=IdentityResolver()
        with self.assertRaises(ValueError): resolver.resolve("slack","x")
        with self.assertRaises(ValueError): resolver.resolve("telegram","")
if __name__ == "__main__": unittest.main()
