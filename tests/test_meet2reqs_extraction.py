"""Tests for the meet2reqs extraction pipeline functions."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import config
from extraction_pipeline import (
    _parse_json_response,
    _format_requirements_doc,
    _format_action_items_doc,
    _format_decisions_doc,
    _format_emphasis_points_doc,
    _get_stem,
    _save_json,
    _save_doc,
)


class TestParseJsonResponse:
    """Tests for the JSON response parser."""

    def setup_method(self):
        self.logger = MagicMock()

    def test_parse_valid_json_array(self):
        response = '[{"id": "REQ-001", "user_story": "As a user..."}]'
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1
        assert result[0]["id"] == "REQ-001"

    def test_parse_json_with_code_fences(self):
        response = '```json\n[{"id": "REQ-001"}]\n```'
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1
        assert result[0]["id"] == "REQ-001"

    def test_parse_json_with_preamble(self):
        response = 'Here are the requirements:\n\n[{"id": "REQ-001"}]'
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1

    def test_parse_empty_array(self):
        response = "[]"
        result = _parse_json_response(response, self.logger)
        assert result == []

    def test_parse_single_object(self):
        response = '{"id": "REQ-001"}'
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1

    def test_parse_invalid_json(self):
        response = "This is not JSON at all"
        result = _parse_json_response(response, self.logger)
        assert result == []
        self.logger.error.assert_called()

    def test_parse_json_with_whitespace(self):
        response = '  \n  [{"id": "REQ-001"}]  \n  '
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1

    def test_parse_json_with_code_fence_no_lang(self):
        response = '```\n[{"id": "ACT-001"}]\n```'
        result = _parse_json_response(response, self.logger)
        assert len(result) == 1


class TestGetStem:
    """Tests for the filename stem extraction."""

    def test_formatted_suffix(self):
        stem = _get_stem("My Transcript - formatted.md")
        assert stem == "My Transcript"

    def test_yaml_suffix(self):
        stem = _get_stem("My Transcript - yaml.md")
        assert stem == "My Transcript"

    def test_legacy_yaml_suffix(self):
        stem = _get_stem("My Transcript_yaml.md")
        assert stem == "My Transcript"

    def test_plain_name(self):
        stem = _get_stem("My Transcript.md")
        assert stem == "My Transcript"

    def test_with_path(self):
        stem = _get_stem("/some/path/My Transcript - formatted.md")
        assert stem == "My Transcript"


class TestFormatDocuments:
    """Tests for Markdown document formatters."""

    def test_format_requirements_doc(self):
        reqs = [{
            "id": "REQ-001",
            "user_story": "As a user, I want login so that I can access the system",
            "role": "user",
            "capability": "login",
            "benefit": "access the system",
            "priority": "high",
            "status": "agreed",
            "speaker": "John",
            "context": "Authentication discussion",
            "source_quotes": ["we need a login system"],
        }]
        doc = _format_requirements_doc(reqs)
        assert "# Requirements" in doc
        assert "REQ-001" in doc
        assert "As a user" in doc
        assert "high" in doc
        assert "we need a login system" in doc

    def test_format_action_items_doc(self):
        items = [{
            "id": "ACT-001",
            "action": "Create the login page",
            "assignee": "Jane",
            "deadline": "End of sprint",
            "priority": "high",
            "status": "assigned",
            "dependencies": ["Design mockup"],
            "context": "UI discussion",
            "source_quotes": ["Jane will create the login page"],
        }]
        doc = _format_action_items_doc(items)
        assert "# Action Items" in doc
        assert "ACT-001" in doc
        assert "Jane" in doc
        assert "Design mockup" in doc

    def test_format_decisions_doc(self):
        decs = [{
            "id": "DEC-001",
            "decision": "Use OAuth2 for authentication",
            "rationale": "Industry standard",
            "alternatives_considered": ["Custom auth", "LDAP"],
            "impact": "All users",
            "decision_maker": "CTO",
            "status": "final",
            "conditions": None,
            "context": "Auth architecture",
            "source_quotes": ["let's go with OAuth2"],
        }]
        doc = _format_decisions_doc(decs)
        assert "# Decisions" in doc
        assert "DEC-001" in doc
        assert "OAuth2" in doc
        assert "Custom auth" in doc

    def test_format_emphasis_points_doc(self):
        emps = [{
            "id": "EMP-001",
            "point": "Security is non-negotiable",
            "emphasis_type": "non-negotiable",
            "speaker": "CTO",
            "strength": "strong",
            "context": "Security discussion",
            "related_to": "REQ-001",
            "source_quotes": ["this is absolutely non-negotiable"],
        }]
        doc = _format_emphasis_points_doc(emps)
        assert "# Emphasis Points" in doc
        assert "EMP-001" in doc
        assert "non-negotiable" in doc

    def test_format_empty_list(self):
        assert "# Requirements" in _format_requirements_doc([])
        assert "# Action Items" in _format_action_items_doc([])
        assert "# Decisions" in _format_decisions_doc([])
        assert "# Emphasis Points" in _format_emphasis_points_doc([])


class TestSaveJson:
    """Tests for JSON save functionality."""

    def test_save_json(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            data = [{"id": "REQ-001", "user_story": "test"}]
            result = _save_json(data, "test-project", " - requirements.json", logger)
            assert result.exists()
            loaded = json.loads(result.read_text(encoding="utf-8"))
            assert loaded[0]["id"] == "REQ-001"

    def test_save_doc(self, tmp_path):
        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            logger = MagicMock()
            content = "# Test Document\n\nContent here."
            result = _save_doc(content, "test-project", " - test.md", logger)
            assert result.exists()
            assert "# Test Document" in result.read_text(encoding="utf-8")


class TestExtractionFunctions:
    """Tests for the main extraction functions (mocked API calls)."""

    def setup_method(self):
        self.logger = MagicMock()
        self.sample_requirements = json.dumps([{
            "id": "REQ-001",
            "user_story": "As a user, I want to log in",
            "role": "user",
            "capability": "log in",
            "benefit": "access the system",
            "priority": "high",
            "status": "agreed",
            "source_quotes": ["we need users to be able to log in"],
            "context": "Auth discussion",
            "speaker": "PM",
        }])

    @patch('extraction_pipeline._generate_summary_with_claude')
    @patch('extraction_pipeline._load_formatted_transcript')
    @patch('extraction_pipeline._load_summary_prompt')
    def test_extract_requirements_returns_list(
        self, mock_prompt, mock_transcript, mock_claude, tmp_path
    ):
        mock_prompt.return_value = "Prompt template {{insert_transcript_text_here}}"
        mock_transcript.return_value = "Sample transcript content"
        mock_claude.return_value = self.sample_requirements

        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            from extraction_pipeline import extract_requirements
            result = extract_requirements("test - formatted.md", logger=self.logger)
            assert len(result) == 1
            assert result[0]["id"] == "REQ-001"

    @patch('extraction_pipeline._generate_summary_with_claude')
    @patch('extraction_pipeline._load_summary_prompt')
    def test_extract_requirements_empty_response(
        self, mock_prompt, mock_claude, tmp_path
    ):
        mock_prompt.return_value = "Prompt"
        mock_claude.return_value = "[]"

        with patch.object(config, 'PROJECTS_DIR', tmp_path):
            from extraction_pipeline import extract_requirements
            result = extract_requirements(
                "test - formatted.md", logger=self.logger,
                transcript_system_message=[{"type": "text", "text": "transcript"}],
            )
            assert result == []
