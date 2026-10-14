import unittest

from calculator import add


class TestAddFunction(unittest.TestCase):
    def test_add_positive_numbers(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative_numbers(self):
        self.assertEqual(add(-2, 2), 0)

    def test_add_mixed_sign_numbers(self):
        self.assertEqual(add(2.5, 1.5), 4.0)


if __name__ == "__main__":
    unittest.main()
