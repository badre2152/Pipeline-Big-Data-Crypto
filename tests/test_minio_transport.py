"""Validate MinIO transport selection without network access."""

import unittest
from unittest.mock import patch

from src.clients.minio_client import get_minio_client
from src.config import MinioConfig


class MinioTransportTests(unittest.TestCase):
    @patch("src.clients.minio_client.boto3.client")
    def test_https_when_secure_enabled(self, client):
        with patch.object(MinioConfig, "SECURE", True), patch.object(
            MinioConfig, "ENDPOINT", "minio.example.com:9000"
        ):
            get_minio_client()
        self.assertEqual(
            client.call_args.kwargs["endpoint_url"], "https://minio.example.com:9000"
        )

    @patch("src.clients.minio_client.boto3.client")
    def test_http_when_secure_disabled(self, client):
        with patch.object(MinioConfig, "SECURE", False), patch.object(
            MinioConfig, "ENDPOINT", "localhost:9000"
        ):
            get_minio_client()
        self.assertEqual(
            client.call_args.kwargs["endpoint_url"], "http://localhost:9000"
        )


if __name__ == "__main__":
    unittest.main()
