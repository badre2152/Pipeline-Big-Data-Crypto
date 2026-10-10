"""Prevent invalid API snapshots from overwriting Bronze data."""

import unittest
from unittest.mock import patch

from src.ingestion.ingest_bronze import save_to_bronze, validate_market_snapshot


class SnapshotValidationTests(unittest.TestCase):
    def test_valid_snapshot(self):
        data = [{"id": "bitcoin"}, {"id": "ethereum"}]
        self.assertEqual(validate_market_snapshot(data), data)

    def test_empty_and_non_list_payloads_are_rejected(self):
        for payload in ([], {}, {"error": "rate limit"}, None):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "empty or invalid"):
                    validate_market_snapshot(payload)

    def test_duplicate_or_missing_coin_ids_are_rejected(self):
        for payload in (
            [{"id": "bitcoin"}, {"id": "bitcoin"}],
            [{"symbol": "btc"}],
            ["bitcoin"],
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_market_snapshot(payload)

    @patch("src.ingestion.ingest_bronze.get_minio_client")
    def test_invalid_data_never_reaches_storage(self, client):
        from datetime import datetime, timezone
        with self.assertRaises(ValueError):
            save_to_bronze([], datetime(2026, 10, 10, tzinfo=timezone.utc))
        client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
