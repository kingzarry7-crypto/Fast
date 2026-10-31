import unittest
from zarry_gateway.identity import IdentityResolver


class GatewayIdentityTests(unittest.TestCase):
    def test_platform_identities_are_isolated_by_default(self):
        resolver = IdentityResolver()
        web = resolver.resolve("web", "123")
        telegram = resolver.resolve("telegram", "123")
        discord = resolver.resolve("discord", "123")
        self.assertEqual(web.subject_id, "web:123")
        self.assertEqual(telegram.subject_id, "telegram:123")
        self.assertEqual(discord.subject_id, "discord:123")
        self.assertEqual(len({web.subject_id, telegram.subject_id, discord.subject_id}), 3)

    def test_display_name_or_username_is_not_an_identity_input(self):
        resolver = IdentityResolver()
        one = resolver.resolve("telegram", "1001")
        two = resolver.resolve("discord", "2002")
        self.assertNotEqual(one.subject_id, two.subject_id)

    def test_explicit_verified_link_lookup_is_the_only_link_path(self):
        resolver = IdentityResolver(verified_link_lookup=lambda platform, external_id: "account-7")
        one = resolver.resolve("telegram", "1001")
        two = resolver.resolve("discord", "2002")
        self.assertEqual(one.subject_id, "account-7")
        self.assertEqual(two.subject_id, "account-7")

    def test_invalid_platform_and_identifier_are_rejected(self):
        resolver = IdentityResolver()
        with self.assertRaises(ValueError):
            resolver.resolve("slack", "x")
        with self.assertRaises(ValueError):
            resolver.resolve("telegram", "")


if __name__ == "__main__":
    unittest.main()
