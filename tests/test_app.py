import os
import unittest
from unittest.mock import patch

from databricks_links_app.app import get_sql_connection_config, greet


class GreetTests(unittest.TestCase):
    def test_greet_default(self) -> None:
        self.assertEqual(greet(), "Hello, world!")

    def test_greet_custom_name(self) -> None:
        self.assertEqual(greet("Ada"), "Hello, Ada!")


class SqlConnectionConfigTests(unittest.TestCase):
    def test_get_sql_connection_config_reads_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABRICKS_HOST": "https://example.cloud.databricks.com",
                "DATABRICKS_HTTP_PATH": "/sql/1.0/warehouses/demo",
                "DATABRICKS_TOKEN": "secret-token",
            },
            clear=True,
        ):
            self.assertEqual(
                get_sql_connection_config(),
                {
                    "server_hostname": "example.cloud.databricks.com",
                    "http_path": "/sql/1.0/warehouses/demo",
                    "access_token": "secret-token",
                },
            )

    def test_get_sql_connection_config_requires_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(get_sql_connection_config())


if __name__ == "__main__":
    unittest.main()
