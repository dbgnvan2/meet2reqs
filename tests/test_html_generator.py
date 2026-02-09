"""Tests for html_generator.py - document generation."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from html_generator import generate_markdown_report


class TestGenerateMarkdownReport(unittest.TestCase):
    """Tests for Markdown report generation."""

    def setUp(self):
        self.extraction = {
            "requirements": [{"user_story": "As a user, I want login", "priority": "high"}],
            "decisions": [{"decision": "Use React", "rationale": "Popular framework", "status": "final"}],
            "action_items": [{"task": "Set up CI", "assignee": "Alice", "deadline": "2026-03-01"}],
            "technology_stack": [{"name": "React", "category": "frontend", "context": "adopted"}],
            "emphasized_items": [{"phrase": "Critical deadline", "speaker": "Bob"}],
        }
        self.enriched = [
            {
                "user_story": "As a user, I want login",
                "priority": "high",
                "acceptance_criteria": ["Given valid creds, When login, Then access dashboard"],
                "functional_requirements": ["The system must authenticate in <2s"],
            }
        ]

    @patch("html_generator.ensure_project_dir")
    def test_markdown_structure(self, mock_ensure):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ensure.return_value = Path(tmpdir)
            md = generate_markdown_report(
                self.extraction, self.enriched, "test-meeting"
            )

            self.assertIn("# Meeting Report", md)
            self.assertIn("## Requirements", md)
            self.assertIn("## Decisions", md)
            self.assertIn("## Action Items", md)
            self.assertIn("## Technology Stack", md)
            self.assertIn("## Emphasized Items", md)

    @patch("html_generator.ensure_project_dir")
    def test_requirements_content(self, mock_ensure):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ensure.return_value = Path(tmpdir)
            md = generate_markdown_report(
                self.extraction, self.enriched, "test"
            )

            self.assertIn("As a user, I want login", md)
            self.assertIn("Acceptance Criteria", md)
            self.assertIn("Functional Requirements", md)

    @patch("html_generator.ensure_project_dir")
    def test_action_items_table(self, mock_ensure):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ensure.return_value = Path(tmpdir)
            md = generate_markdown_report(
                self.extraction, self.enriched, "test"
            )

            self.assertIn("| # | Task | Assignee | Deadline |", md)
            self.assertIn("Set up CI", md)
            self.assertIn("Alice", md)

    @patch("html_generator.ensure_project_dir")
    def test_validation_score(self, mock_ensure):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ensure.return_value = Path(tmpdir)
            report = {"overall_score": 0.85}
            md = generate_markdown_report(
                self.extraction, self.enriched, "test",
                validation_report=report,
            )

            self.assertIn("Validation", md)
            self.assertIn("85%", md)

    @patch("html_generator.ensure_project_dir")
    def test_empty_extraction(self, mock_ensure):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ensure.return_value = Path(tmpdir)
            empty = {cat: [] for cat in config.EXTRACTION_CATEGORIES}
            md = generate_markdown_report(empty, [], "test")

            self.assertIn("# Meeting Report", md)
            self.assertNotIn("## Requirements", md)

    @patch("html_generator.ensure_project_dir")
    def test_file_saved(self, mock_ensure):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_ensure.return_value = Path(tmpdir)
            generate_markdown_report(
                self.extraction, self.enriched, "test"
            )
            output = Path(tmpdir) / f"test{config.SUFFIX_REPORT_MD}"
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
