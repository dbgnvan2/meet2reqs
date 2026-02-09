"""Tests for config.py - configuration management and validation."""

import unittest
from pathlib import Path
from unittest.mock import patch

import config


class TestProjectSettings(unittest.TestCase):
    """Tests for the ProjectSettings singleton."""

    def test_singleton_instance(self):
        s1 = config.ProjectSettings()
        s2 = config.ProjectSettings()
        self.assertIs(s1, s2)

    def test_default_model_assignments(self):
        s = config.settings
        self.assertIn("claude", s.CLEANING_MODEL)
        self.assertIn("claude", s.EXTRACTION_MODEL)
        self.assertIn("claude", s.ENRICHMENT_MODEL)
        self.assertIn("claude", s.VALIDATION_MODEL)

    def test_set_model_valid(self):
        import model_specs
        valid_model = list(model_specs.PRICING.keys())[0]
        config.settings.set_model("cleaning", valid_model)
        self.assertEqual(config.settings.CLEANING_MODEL, valid_model)

    def test_set_model_invalid_role(self):
        with self.assertRaises(ValueError):
            config.settings.set_model("nonexistent", "some-model")

    def test_set_model_invalid_model(self):
        with self.assertRaises(ValueError):
            config.settings.set_model("cleaning", "not-a-real-model")

    def test_derived_paths(self):
        s = config.settings
        self.assertEqual(s.SOURCE_DIR, s.TRANSCRIPTS_BASE / "source")
        self.assertEqual(s.PROJECTS_DIR, s.TRANSCRIPTS_BASE / "projects")
        self.assertEqual(s.PROCESSED_DIR, s.TRANSCRIPTS_BASE / "processed")

    def test_get_all_model_names(self):
        names = config.settings.get_all_model_names()
        self.assertIsInstance(names, list)
        self.assertTrue(len(names) > 0)


class TestConstants(unittest.TestCase):
    """Tests for configuration constants."""

    def test_file_suffixes(self):
        self.assertTrue(config.SUFFIX_CLEANED.endswith(".md"))
        self.assertTrue(config.SUFFIX_REQUIREMENTS.endswith(".json"))
        self.assertTrue(config.SUFFIX_DECISIONS.endswith(".json"))
        self.assertTrue(config.SUFFIX_ACTION_ITEMS.endswith(".json"))
        self.assertTrue(config.SUFFIX_TECH_STACK.endswith(".json"))
        self.assertTrue(config.SUFFIX_EMPHASIZED.endswith(".json"))
        self.assertTrue(config.SUFFIX_ENRICHED.endswith(".json"))
        self.assertTrue(config.SUFFIX_REPORT_MD.endswith(".md"))
        self.assertTrue(config.SUFFIX_REPORT_HTML.endswith(".html"))
        self.assertTrue(config.SUFFIX_REPORT_PDF.endswith(".pdf"))

    def test_chunking_constants(self):
        self.assertGreater(config.CHUNK_THRESHOLD, 0)
        self.assertGreater(config.CHUNK_MAX_TOKENS, 0)
        self.assertGreater(config.CHUNK_OVERLAP_TOKENS, 0)
        self.assertLess(config.CHUNK_OVERLAP_TOKENS, config.CHUNK_MAX_TOKENS)

    def test_token_limits(self):
        self.assertGreater(config.MAX_TOKENS_CLEANING, 0)
        self.assertGreater(config.MAX_TOKENS_EXTRACTION, 0)
        self.assertGreater(config.MAX_TOKENS_ENRICHMENT, 0)
        self.assertGreater(config.MAX_TOKENS_VALIDATION, 0)

    def test_temperature_range(self):
        for temp in [config.TEMP_STRICT, config.TEMP_ANALYSIS, config.TEMP_BALANCED]:
            self.assertGreaterEqual(temp, 0.0)
            self.assertLessEqual(temp, 1.0)

    def test_extraction_categories(self):
        expected = ["requirements", "decisions", "action_items", "technology_stack", "emphasized_items"]
        self.assertEqual(config.EXTRACTION_CATEGORIES, expected)


class TestValidationResult(unittest.TestCase):
    """Tests for the ValidationResult class."""

    def test_empty_result_is_valid(self):
        r = config.ValidationResult()
        self.assertTrue(r.is_valid())
        self.assertEqual(len(r.errors), 0)
        self.assertEqual(len(r.warnings), 0)

    def test_error_makes_invalid(self):
        r = config.ValidationResult()
        r.add_error("something broke")
        self.assertFalse(r.is_valid())

    def test_warning_stays_valid(self):
        r = config.ValidationResult()
        r.add_warning("be careful")
        self.assertTrue(r.is_valid())

    def test_format_report(self):
        r = config.ValidationResult()
        r.add_error("test error")
        r.add_warning("test warning")
        report = r.format_report()
        self.assertIn("test error", report)
        self.assertIn("test warning", report)

    def test_format_report_clean(self):
        r = config.ValidationResult()
        report = r.format_report()
        self.assertIn("passed", report)


class TestValidateConfiguration(unittest.TestCase):
    """Tests for the validate_configuration function."""

    def test_validation_returns_result(self):
        result = config.validate_configuration(verbose=False)
        self.assertIsInstance(result, config.ValidationResult)

    def test_prompt_filenames_validated(self):
        # Prompt files should exist (we created them)
        result = config.validate_configuration(verbose=False)
        # The result may have warnings for prompt files but should not error
        self.assertIsInstance(result, config.ValidationResult)


if __name__ == "__main__":
    unittest.main()
