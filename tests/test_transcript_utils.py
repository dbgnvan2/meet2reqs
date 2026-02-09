"""Tests for transcript_utils.py - shared utility functions."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import config
from transcript_utils import (
    check_token_budget,
    clean_project_name,
    estimate_token_count,
    extract_section,
    find_text_in_content,
    format_file_size,
    load_prompt,
    markdown_to_html,
    normalize_text,
    sanitize_filename,
    strip_yaml_frontmatter,
    validate_input_file,
)


class TestSanitizeFilename(unittest.TestCase):
    def test_basic_filename(self):
        self.assertEqual(sanitize_filename("hello.txt"), "hello.txt")

    def test_path_traversal(self):
        result = sanitize_filename("../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_null_bytes(self):
        result = sanitize_filename("file\x00.txt")
        self.assertNotIn("\x00", result)

    def test_empty_after_sanitize(self):
        with self.assertRaises(ValueError):
            sanitize_filename("../")

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            sanitize_filename("")

    def test_none_input(self):
        with self.assertRaises(ValueError):
            sanitize_filename(None)

    def test_long_filename(self):
        with self.assertRaises(ValueError):
            sanitize_filename("x" * 300)


class TestCleanProjectName(unittest.TestCase):
    def test_basic_name(self):
        self.assertEqual(clean_project_name("meeting-notes.txt"), "meeting-notes")

    def test_strip_validated(self):
        self.assertEqual(clean_project_name("meeting_validated.json"), "meeting")

    def test_strip_version(self):
        self.assertEqual(clean_project_name("meeting_v2.json"), "meeting")

    def test_multiple_suffixes(self):
        self.assertEqual(clean_project_name("meeting_v2_validated.json"), "meeting")


class TestEstimateTokenCount(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(estimate_token_count(""), 0)

    def test_known_length(self):
        text = "a" * 400
        self.assertEqual(estimate_token_count(text), 100)

    def test_real_text(self):
        text = "Hello world, this is a test."
        result = estimate_token_count(text)
        self.assertGreater(result, 0)


class TestCheckTokenBudget(unittest.TestCase):
    def test_within_budget(self):
        self.assertTrue(check_token_budget("short text", 10000))

    def test_exceeds_budget(self):
        long_text = "x" * 100000
        self.assertFalse(check_token_budget(long_text, 100))


class TestNormalizeText(unittest.TestCase):
    def test_basic(self):
        result = normalize_text("Hello World")
        self.assertEqual(result, "hello world")

    def test_timestamps(self):
        result = normalize_text("At 10:30am the meeting started")
        self.assertNotIn("10:30", result)

    def test_html_tags(self):
        result = normalize_text("<p>Hello</p>")
        self.assertNotIn("<p>", result)

    def test_aggressive_speaker_tags(self):
        result = normalize_text("**John:** Hello everyone", aggressive=True)
        self.assertNotIn("John:", result)


class TestFindTextInContent(unittest.TestCase):
    def test_exact_match(self):
        start, end, ratio = find_text_in_content("hello world", "say hello world today")
        self.assertIsNotNone(start)
        self.assertEqual(ratio, 1.0)

    def test_no_match(self):
        start, end, ratio = find_text_in_content("xyzzy", "completely different text")
        self.assertIsNone(start)
        self.assertLess(ratio, config.FUZZY_MATCH_THRESHOLD)

    def test_fuzzy_match(self):
        start, end, ratio = find_text_in_content(
            "the quick brown fox",
            "here is the quick brown fox jumping",
        )
        self.assertIsNotNone(start)
        self.assertGreaterEqual(ratio, config.FUZZY_MATCH_THRESHOLD)


class TestExtractSection(unittest.TestCase):
    def test_extract_existing(self):
        content = "# Title\n## Requirements\nSome content here\n## Decisions\nOther content"
        result = extract_section(content, "Requirements")
        self.assertIn("Some content", result)
        self.assertNotIn("Other content", result)

    def test_extract_missing(self):
        content = "# Title\n## Something Else\nContent"
        result = extract_section(content, "Requirements")
        self.assertEqual(result, "")

    def test_extract_last_section(self):
        content = "## First\nAAA\n## Second\nBBB"
        result = extract_section(content, "Second")
        self.assertIn("BBB", result)


class TestStripYamlFrontmatter(unittest.TestCase):
    def test_with_frontmatter(self):
        content = "---\ntitle: Test\n---\nActual content"
        result = strip_yaml_frontmatter(content)
        self.assertIn("Actual content", result)
        self.assertNotIn("title:", result)

    def test_without_frontmatter(self):
        content = "Just regular content"
        result = strip_yaml_frontmatter(content)
        self.assertEqual(result, content)


class TestMarkdownToHtml(unittest.TestCase):
    def test_headers(self):
        result = markdown_to_html("# Title")
        self.assertIn("<h1>Title</h1>", result)

    def test_bold(self):
        result = markdown_to_html("**bold text**")
        self.assertIn("<strong>bold text</strong>", result)

    def test_italic(self):
        result = markdown_to_html("*italic text*")
        self.assertIn("<em>italic text</em>", result)


class TestFormatFileSize(unittest.TestCase):
    def test_bytes(self):
        self.assertIn("B", format_file_size(500))

    def test_kilobytes(self):
        self.assertIn("KB", format_file_size(2048))

    def test_megabytes(self):
        self.assertIn("MB", format_file_size(2 * 1024 * 1024))


class TestValidateInputFile(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            validate_input_file(Path("/nonexistent/file.txt"))

    def test_valid_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("content")
            f.flush()
            validate_input_file(Path(f.name))
            Path(f.name).unlink()


class TestLoadPrompt(unittest.TestCase):
    def test_load_existing(self):
        text = load_prompt("cleaning.md")
        self.assertIn("Clean", text)

    def test_load_missing(self):
        with self.assertRaises(FileNotFoundError):
            load_prompt("nonexistent_prompt.md")


if __name__ == "__main__":
    unittest.main()
