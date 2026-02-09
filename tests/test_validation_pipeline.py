"""Tests for validation_pipeline.py - extraction validation."""

import unittest

from validation_pipeline import (
    _calculate_score,
    _validate_enrichment,
    _validate_fidelity,
    _validate_invest,
    _validate_structure,
)


class TestValidateStructure(unittest.TestCase):
    """Tests for JSON structure validation."""

    def test_valid_requirements(self):
        items = [{"user_story": "As a user, I want X"}]
        result = _validate_structure("requirements", items)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["valid"], 1)
        self.assertEqual(len(result["issues"]), 0)

    def test_missing_required_field(self):
        items = [{"priority": "high"}]  # missing user_story
        result = _validate_structure("requirements", items)
        self.assertEqual(result["valid"], 0)
        self.assertEqual(len(result["issues"]), 1)

    def test_valid_decisions(self):
        items = [{"decision": "Use React", "rationale": "Popular"}]
        result = _validate_structure("decisions", items)
        self.assertEqual(result["valid"], 1)

    def test_non_dict_item(self):
        items = ["not a dict"]
        result = _validate_structure("requirements", items)
        self.assertEqual(result["valid"], 0)
        self.assertEqual(len(result["issues"]), 1)

    def test_empty_list(self):
        result = _validate_structure("requirements", [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["valid"], 0)

    def test_valid_action_items(self):
        items = [{"task": "Set up CI/CD"}]
        result = _validate_structure("action_items", items)
        self.assertEqual(result["valid"], 1)

    def test_valid_tech_stack(self):
        items = [{"name": "PostgreSQL"}]
        result = _validate_structure("technology_stack", items)
        self.assertEqual(result["valid"], 1)

    def test_valid_emphasized(self):
        items = [{"phrase": "This is important"}]
        result = _validate_structure("emphasized_items", items)
        self.assertEqual(result["valid"], 1)


class TestValidateFidelity(unittest.TestCase):
    """Tests for fidelity checking against transcript."""

    def test_decision_found(self):
        extraction = {"decisions": [{"decision": "we should use React"}], "emphasized_items": []}
        transcript = "After discussion, we should use React for the frontend."
        result = _validate_fidelity(extraction, transcript)
        self.assertEqual(result["decisions"]["found"], 1)

    def test_decision_not_found(self):
        extraction = {"decisions": [{"decision": "completely fabricated decision"}], "emphasized_items": []}
        transcript = "Meeting about project planning."
        result = _validate_fidelity(extraction, transcript)
        self.assertEqual(result["decisions"]["found"], 0)

    def test_emphasis_found(self):
        extraction = {"decisions": [], "emphasized_items": [{"phrase": "critical deadline"}]}
        transcript = "We have a critical deadline next week."
        result = _validate_fidelity(extraction, transcript)
        self.assertEqual(result["emphasized_items"]["found"], 1)


class TestValidateInvest(unittest.TestCase):
    """Tests for INVEST compliance checking."""

    def test_compliant_story(self):
        requirements = [{"user_story": "As a user, I want to login so that I can access my account"}]
        result = _validate_invest(requirements)
        self.assertEqual(result["compliant"], 1)

    def test_missing_role(self):
        requirements = [{"user_story": "I want to login so that I can access my account"}]
        result = _validate_invest(requirements)
        self.assertEqual(result["compliant"], 0)

    def test_missing_benefit(self):
        requirements = [{"user_story": "As a user, I want to login"}]
        result = _validate_invest(requirements)
        self.assertEqual(result["compliant"], 0)

    def test_alternative_phrasing(self):
        requirements = [{"user_story": "As a developer, I need API docs in order to integrate faster"}]
        result = _validate_invest(requirements)
        self.assertEqual(result["compliant"], 1)

    def test_empty_story(self):
        requirements = [{"user_story": ""}]
        result = _validate_invest(requirements)
        self.assertEqual(result["checked"], 0)


class TestValidateEnrichment(unittest.TestCase):
    """Tests for enrichment quality checking."""

    def test_proper_gwt(self):
        enriched = [{
            "acceptance_criteria": [
                "Given a user exists, When they login, Then they see the dashboard"
            ],
        }]
        result = _validate_enrichment(enriched)
        self.assertEqual(result["good"], 1)

    def test_missing_gwt(self):
        enriched = [{
            "acceptance_criteria": ["User should be able to login"],
        }]
        result = _validate_enrichment(enriched)
        self.assertEqual(result["good"], 0)

    def test_no_criteria(self):
        enriched = [{"acceptance_criteria": []}]
        result = _validate_enrichment(enriched)
        self.assertEqual(len(result["issues"]), 1)

    def test_empty_input(self):
        result = _validate_enrichment([])
        self.assertEqual(result["checked"], 0)


class TestCalculateScore(unittest.TestCase):
    """Tests for overall score calculation."""

    def test_perfect_score(self):
        report = {
            "categories": {
                "requirements": {"count": 3, "valid": 3},
                "decisions": {"count": 2, "valid": 2},
            },
        }
        score = _calculate_score(report)
        self.assertAlmostEqual(score, 1.0)

    def test_zero_score(self):
        report = {
            "categories": {
                "requirements": {"count": 5, "valid": 0},
            },
        }
        score = _calculate_score(report)
        self.assertAlmostEqual(score, 0.0)

    def test_partial_score(self):
        report = {
            "categories": {
                "requirements": {"count": 4, "valid": 2},
            },
        }
        score = _calculate_score(report)
        self.assertAlmostEqual(score, 0.5)

    def test_empty_report(self):
        report = {"categories": {}}
        score = _calculate_score(report)
        self.assertAlmostEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
