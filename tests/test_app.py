import unittest

from databricks_links_app.app import greet


class GreetTests(unittest.TestCase):
    def test_greet_default(self) -> None:
        self.assertEqual(greet(), "Hello, world!")

    def test_greet_custom_name(self) -> None:
        self.assertEqual(greet("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
