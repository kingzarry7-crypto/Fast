import unittest
from work_intent import parse

class WorkIntentTests(unittest.TestCase):
    def test_explicit_prefix_creates_work(self):
        item = parse("KZ, find me 5 legitimate website clients this week")
        self.assertEqual(item["kind"], "create")
        self.assertIn("find me 5", item["goal"].lower())

    def test_natural_work_phrase_creates_work(self):
        item = parse("please find me some freelance opportunities")
        self.assertEqual(item["kind"], "create")

    def test_approval(self):
        item = parse("KZ approve 12345678-abcd")
        self.assertEqual(item["kind"], "approve")
        self.assertEqual(item["workflow_id"], "12345678-abcd")

    def test_rejection(self):
        item = parse("reject work 12345678-abcd")
        self.assertEqual(item["kind"], "reject")

    def test_status(self):
        item = parse("show work status 12345678-abcd")
        self.assertEqual(item["kind"], "status")


    def test_do_everything_yourself_creates_work(self):
        item = parse("Fix everything yourself and the job name is web developer")
        self.assertEqual(item["kind"], "create")
        self.assertIn("web developer", item["goal"].lower())

    def test_normal_chat_is_not_work(self):
        self.assertIsNone(parse("What is Bitcoin?"))
        self.assertIsNone(parse("Can you explain how websites work?"))

if __name__ == "__main__":
    unittest.main()


class NaturalWorkContinuationTests(unittest.TestCase):
    def test_continuation_intent(self):
        item = parse('continue this for me and finish the client research')
        self.assertEqual(item['kind'], 'create')
        self.assertIn('client research', item['goal'])
