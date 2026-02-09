"""Tests for enrichment_pipeline.py - user story enrichment."""

import json
import unittest
from unittest.mock import MagicMock, patch

from enrichment_pipeline import _parse_enrichment_response


class TestParseEnrichmentResponse(unittest.TestCase):
    """Tests for enrichment JSON parsing."""

    def test_valid_enrichment(self):
        enriched = [
            {
                "user_story": "As a user, I want login",
                "acceptance_criteria": [
                    "Given a valid user, When they submit credentials, Then they are logged in"
                ],
                "functional_requirements": ["The system must authenticate users within 2 seconds"],
                "confidence": "high",
            }
        ]
        result = _parse_enrichment_response(json.dumps(enriched), [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["confidence"], "high")
        self.assertEqual(len(result[0]["acceptance_criteria"]), 1)

    def test_code_fence_response(self):
        enriched = [{"user_story": "test", "acceptance_criteria": [], "functional_requirements": [], "confidence": "medium"}]
        response = f"```json\n{json.dumps(enriched)}\n```"
        result = _parse_enrichment_response(response, [])
        self.assertEqual(len(result), 1)

    def test_invalid_json_fallback(self):
        originals = [{"user_story": "As a dev, I want tests"}]
        result = _parse_enrichment_response("invalid json", originals)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["confidence"], "low")
        self.assertEqual(result[0]["acceptance_criteria"], [])

    def test_missing_fields_added(self):
        enriched = [{"user_story": "test story"}]
        result = _parse_enrichment_response(json.dumps(enriched), [])
        self.assertIn("acceptance_criteria", result[0])
        self.assertIn("functional_requirements", result[0])
        self.assertIn("confidence", result[0])

    def test_non_array_response(self):
        result = _parse_enrichment_response(
            json.dumps({"not": "an array"}),
            [{"user_story": "fallback"}],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
