import unittest

from skill_registry import SKILLS, classify_skill_request, get_skill, list_skills


class SkillRegistryTests(unittest.TestCase):
    def test_expected_six_skills_are_registered(self):
        ids = {skill["id"] for skill in list_skills()}
        self.assertEqual(ids, {"coding", "web", "images", "github", "testing", "data"})

    def test_every_skill_has_policy_and_execution_metadata(self):
        for skill in SKILLS:
            with self.subTest(skill=skill["id"]):
                self.assertTrue(skill["description"])
                self.assertTrue(skill["tools"])
                self.assertTrue(skill["execution"])
                self.assertTrue(skill["approval"])

    def test_request_classifier_routes_common_intents(self):
        cases = {
            "Build a Next.js app": "coding",
            "Research the latest browser APIs": "web",
            "Create an image for my store": "images",
            "Review my GitHub repository": "github",
            "Debug this failing unit test": "testing",
            "Analyze this CSV dataset": "data",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(classify_skill_request(prompt), expected)

    def test_unknown_skill_is_not_silently_selected(self):
        self.assertIsNone(get_skill("not-a-real-skill"))


if __name__ == "__main__":
    unittest.main()
