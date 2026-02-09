"""Tests for the meet2reqs extraction validation pipeline."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import config
from validation_pipeline import (
    _validate_source_quotes,
    validate_extraction,
    _save_validation_report,
)


class TestValidateSourceQuotes:
    """Tests for source quote fidelity validation."""

    def setup_method(self):
        self.logger = MagicMock()
        self.transcript = (
            "Good morning everyone. Today we need to discuss the new login system. "
            "I think we should use OAuth2 for authentication because it's the industry standard. "
            "Jane, can you create the login page by end of sprint? "
            "This is absolutely critical - security is non-negotiable. "
            "We've decided to go with the cloud deployment approach."
        )

    def test_exact_match(self):
        items = [{
            "id": "REQ-001",
            "source_quotes": ["we should use OAuth2 for authentication"],
        }]
        results = _validate_source_quotes(items, self.transcript, "requirement", self.logger)
        assert len(results) == 1
        assert results[0]["status"] in ("valid", "partial")
        assert results[0]["fidelity_score"] > 0.8

    def test_no_match(self):
        items = [{
            "id": "REQ-001",
            "source_quotes": ["this quote does not exist anywhere in the transcript at all"],
        }]
        results = _validate_source_quotes(items, self.transcript, "requirement", self.logger)
        assert len(results) == 1
        assert results[0]["status"] == "invalid"

    def test_no_quotes_provided(self):
        items = [{
            "id": "REQ-001",
            "source_quotes": [],
        }]
        results = _validate_source_quotes(items, self.transcript, "requirement", self.logger)
        assert len(results) == 1
        assert results[0]["status"] == "no_quotes"

    def test_multiple_items(self):
        items = [
            {
                "id": "REQ-001",
                "source_quotes": ["use OAuth2 for authentication"],
            },
            {
                "id": "ACT-001",
                "source_quotes": ["create the login page by end of sprint"],
            },
        ]
        results = _validate_source_quotes(items, self.transcript, "requirement", self.logger)
        assert len(results) == 2

    def test_partial_match(self):
        items = [{
            "id": "REQ-001",
            "source_quotes": ["I think we should use OAuth2 for authentication because it is the industry standard"],
        }]
        results = _validate_source_quotes(items, self.transcript, "requirement", self.logger)
        assert len(results) == 1
        # Should match since most words exist in the transcript
        assert results[0]["fidelity_score"] > 0.5

    def test_short_quote_skipped(self):
        items = [{
            "id": "REQ-001",
            "source_quotes": ["yes"],
        }]
        results = _validate_source_quotes(items, self.transcript, "requirement", self.logger)
        assert results[0]["quote_details"][0]["status"] == "too_short"


class TestValidateExtraction:
    """Tests for the full extraction validation pipeline."""

    def test_validate_with_valid_data(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            stem = "test-project"
            project_dir = tmp_path / stem
            project_dir.mkdir()

            # Write formatted transcript
            transcript = (
                "We need a login system. Jane will create the login page. "
                "We decided to use OAuth2. Security is very important."
            )
            (project_dir / f"{stem}{config.SUFFIX_FORMATTED}").write_text(transcript)

            # Create extraction results
            results = {
                "requirements": [{
                    "id": "REQ-001",
                    "user_story": "As a user, I want login",
                    "source_quotes": ["We need a login system"],
                }],
                "action_items": [{
                    "id": "ACT-001",
                    "action": "Create login page",
                    "source_quotes": ["Jane will create the login page"],
                }],
                "decisions": [{
                    "id": "DEC-001",
                    "decision": "Use OAuth2",
                    "source_quotes": ["We decided to use OAuth2"],
                }],
                "emphasis_points": [{
                    "id": "EMP-001",
                    "point": "Security is important",
                    "source_quotes": ["Security is very important"],
                }],
            }

            report = validate_extraction(stem, results, logger)
            assert report["overall"]["total_items"] == 4
            assert report["overall"]["recommendation"] in ("pass", "review")

    def test_validate_with_missing_files(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            report = validate_extraction("nonexistent-project", logger=logger)
            assert "error" in report

    def test_validate_loads_from_json_files(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            stem = "test-project"
            project_dir = tmp_path / stem
            project_dir.mkdir()

            # Write transcript
            transcript = "We need a login system for all users."
            (project_dir / f"{stem}{config.SUFFIX_FORMATTED}").write_text(transcript)

            # Write JSON files
            reqs = [{"id": "REQ-001", "source_quotes": ["We need a login system"]}]
            (project_dir / f"{stem}{config.SUFFIX_REQUIREMENTS}").write_text(
                json.dumps(reqs)
            )

            report = validate_extraction(stem, logger=logger)
            assert report["overall"]["total_items"] >= 1


class TestSaveValidationReport:
    """Tests for validation report saving."""

    def test_saves_json_and_markdown(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            report = {
                "base_name": "test",
                "type_summaries": {
                    "requirement": {"total": 1, "valid": 1, "partial": 0, "invalid": 0, "no_quotes": 0},
                },
                "overall": {
                    "total_items": 1,
                    "valid": 1,
                    "partial": 0,
                    "invalid": 0,
                    "fidelity_score": 1.0,
                    "structure_issues": 0,
                    "recommendation": "pass",
                },
                "validation_details": [],
                "structure_issues": [],
            }
            result = _save_validation_report(report, "test", logger)
            assert result.exists()
            assert "Validation" in result.read_text(encoding="utf-8")

            # Check JSON also exists
            json_path = tmp_path / "test" / "test - extraction-validation.json"
            assert json_path.exists()
