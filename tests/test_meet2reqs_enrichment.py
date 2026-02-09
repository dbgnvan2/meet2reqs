"""Tests for the meet2reqs enrichment pipeline."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import config
from enrichment_pipeline import (
    _parse_json_response,
    _format_enriched_requirements_doc,
    _load_enrichment_templates,
    save_enriched_requirements,
)


class TestEnrichmentParseJson:
    """Tests for enrichment JSON parsing."""

    def setup_method(self):
        self.logger = MagicMock()

    def test_parse_valid_enrichment(self):
        response = json.dumps([{
            "id": "REQ-001",
            "user_story": "As a user...",
            "acceptance_criteria": [
                {"id": "REQ-001-AC-01", "given": "a user", "when": "login", "then": "access granted"}
            ],
            "functional_requirements": [
                {"id": "REQ-001-FR-01", "requirement": "The system must authenticate users"}
            ],
        }])
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1
        assert len(result[0]["acceptance_criteria"]) == 1
        assert len(result[0]["functional_requirements"]) == 1

    def test_parse_with_code_fences(self):
        response = '```json\n[{"id": "REQ-001"}]\n```'
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1

    def test_parse_invalid_returns_empty(self):
        result = _parse_json_response("not json", self.logger)
        assert result == []


class TestEnrichmentTemplates:
    """Tests for loading enrichment templates."""

    def test_load_templates_structure(self):
        templates = _load_enrichment_templates()
        assert "acceptance_criteria_patterns" in templates
        assert "functional_requirement_patterns" in templates
        assert "invest_checklist" in templates
        assert "smart_checklist" in templates

    def test_templates_have_patterns(self):
        templates = _load_enrichment_templates()
        patterns = templates["acceptance_criteria_patterns"]["patterns"]
        assert "data_handling" in patterns
        assert "user_interaction" in patterns
        assert "integration" in patterns

    def test_functional_patterns_exist(self):
        templates = _load_enrichment_templates()
        fr_patterns = templates["functional_requirement_patterns"]["patterns"]
        assert "data_validation" in fr_patterns
        assert "error_handling" in fr_patterns

    def test_invest_criteria(self):
        templates = _load_enrichment_templates()
        invest = templates["invest_checklist"]["criteria"]
        assert "independent" in invest
        assert "valuable" in invest
        assert "testable" in invest


class TestFormatEnrichedDoc:
    """Tests for enriched requirements Markdown formatting."""

    def test_format_with_acceptance_criteria(self):
        enriched = [{
            "id": "REQ-001",
            "user_story": "As a user, I want login",
            "acceptance_criteria": [
                {
                    "id": "REQ-001-AC-01",
                    "given": "a registered user",
                    "when": "they enter valid credentials",
                    "then": "they are granted access",
                }
            ],
            "functional_requirements": [
                {
                    "id": "REQ-001-FR-01",
                    "requirement": "The system must authenticate users via OAuth2",
                }
            ],
        }]
        doc = _format_enriched_requirements_doc(enriched)
        assert "# Enriched Requirements" in doc
        assert "REQ-001" in doc
        assert "Acceptance Criteria" in doc
        assert "Given" in doc
        assert "When" in doc
        assert "Then" in doc
        assert "Functional Requirements" in doc
        assert "OAuth2" in doc

    def test_format_empty_list(self):
        doc = _format_enriched_requirements_doc([])
        assert "# Enriched Requirements" in doc

    def test_format_no_criteria(self):
        enriched = [{
            "id": "REQ-001",
            "user_story": "As a user, I want login",
            "acceptance_criteria": [],
            "functional_requirements": [],
        }]
        doc = _format_enriched_requirements_doc(enriched)
        assert "REQ-001" in doc


class TestSaveEnrichedRequirements:
    """Tests for saving enriched requirements."""

    def test_save_creates_files(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            enriched = [{
                "id": "REQ-001",
                "user_story": "As a user...",
                "acceptance_criteria": [],
                "functional_requirements": [],
            }]
            json_path, doc_path = save_enriched_requirements(enriched, "test-project", logger)
            assert json_path.exists()
            assert doc_path.exists()

            # Verify JSON
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            assert loaded[0]["id"] == "REQ-001"

            # Verify Markdown
            doc_content = doc_path.read_text(encoding="utf-8")
            assert "REQ-001" in doc_content
