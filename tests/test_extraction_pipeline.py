"""Tests for extraction_pipeline.py - multi-output extraction."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import config
from extraction_pipeline import _parse_extraction_response, _save_extraction_files


class TestParseExtractionResponse(unittest.TestCase):
    """Tests for JSON response parsing."""

    def test_valid_json(self):
        response = json.dumps({
            "requirements": [{"user_story": "As a user, I want login"}],
            "decisions": [{"decision": "Use React", "rationale": "Popular"}],
            "action_items": [{"task": "Set up repo"}],
            "technology_stack": [{"name": "React"}],
            "emphasized_items": [{"phrase": "This is critical"}],
        })
        result = _parse_extraction_response(response)
        self.assertEqual(len(result["requirements"]), 1)
        self.assertEqual(len(result["decisions"]), 1)
        self.assertEqual(len(result["action_items"]), 1)

    def test_json_with_code_fence(self):
        response = '```json\n{"requirements": [], "decisions": [], "action_items": [], "technology_stack": [], "emphasized_items": []}\n```'
        result = _parse_extraction_response(response)
        self.assertIn("requirements", result)

    def test_invalid_json(self):
        result = _parse_extraction_response("not json at all")
        for cat in config.EXTRACTION_CATEGORIES:
            self.assertEqual(result[cat], [])

    def test_missing_categories(self):
        response = json.dumps({"requirements": [{"user_story": "test"}]})
        result = _parse_extraction_response(response)
        self.assertEqual(len(result["requirements"]), 1)
        self.assertEqual(result["decisions"], [])
        self.assertEqual(result["action_items"], [])

    def test_non_list_category(self):
        response = json.dumps({"requirements": "not a list", "decisions": [], "action_items": [], "technology_stack": [], "emphasized_items": []})
        result = _parse_extraction_response(response)
        self.assertEqual(result["requirements"], [])


class TestSaveExtractionFiles(unittest.TestCase):
    """Tests for saving extraction results to files."""

    def test_save_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            extraction = {
                "requirements": [{"user_story": "test"}],
                "decisions": [],
                "action_items": [],
                "technology_stack": [],
                "emphasized_items": [],
            }
            _save_extraction_files(extraction, "test-meeting", project_dir)

            req_file = project_dir / f"test-meeting{config.SUFFIX_REQUIREMENTS}"
            self.assertTrue(req_file.exists())
            data = json.loads(req_file.read_text())
            self.assertEqual(len(data), 1)

    def test_empty_categories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            extraction = {cat: [] for cat in config.EXTRACTION_CATEGORIES}
            _save_extraction_files(extraction, "test", project_dir)

            for suffix in [config.SUFFIX_REQUIREMENTS, config.SUFFIX_DECISIONS]:
                f = project_dir / f"test{suffix}"
                self.assertTrue(f.exists())
                self.assertEqual(json.loads(f.read_text()), [])


if __name__ == "__main__":
    unittest.main()
