"""Tests for chunking.py - transcript chunking and aggregation."""

import unittest

import config
from chunking import (
    aggregate_extractions,
    chunk_text,
    count_tokens,
    needs_chunking,
    _dedup_key,
    _find_split_points,
)


class TestCountTokens(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(count_tokens(""), 0)

    def test_known_text(self):
        result = count_tokens("Hello, this is a test.")
        self.assertGreater(result, 0)


class TestNeedsChunking(unittest.TestCase):
    def test_short_text(self):
        self.assertFalse(needs_chunking("short text"))

    def test_long_text(self):
        # Create text that exceeds threshold
        long_text = "word " * (config.CHUNK_THRESHOLD * config.CHARS_PER_TOKEN)
        self.assertTrue(needs_chunking(long_text))


class TestFindSplitPoints(unittest.TestCase):
    def test_paragraph_breaks(self):
        text = "First paragraph.\n\nSecond paragraph."
        points = _find_split_points(text)
        self.assertTrue(len(points) > 0)

    def test_speaker_labels(self):
        text = "Some text.\n**Alice:** Hello\n**Bob:** Hi"
        points = _find_split_points(text)
        self.assertTrue(len(points) > 0)

    def test_no_breaks(self):
        text = "One continuous text without any breaks at all"
        points = _find_split_points(text)
        # Should fall back to single newlines (none here)
        self.assertEqual(len(points), 0)


class TestChunkText(unittest.TestCase):
    def test_short_text_single_chunk(self):
        result = chunk_text("short text", max_tokens=1000)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["index"], 0)
        self.assertEqual(result[0]["text"], "short text")

    def test_long_text_multiple_chunks(self):
        # Build text with natural break points
        paragraphs = ["Paragraph {}\n\n".format(i) * 50 for i in range(20)]
        text = "".join(paragraphs)
        result = chunk_text(text, max_tokens=100, overlap_tokens=10)
        self.assertGreater(len(result), 1)
        for chunk in result:
            self.assertIn("index", chunk)
            self.assertIn("text", chunk)
            self.assertIn("tokens", chunk)

    def test_chunk_indices_sequential(self):
        text = ("Word " * 200 + "\n\n") * 10
        result = chunk_text(text, max_tokens=100)
        for i, chunk in enumerate(result):
            self.assertEqual(chunk["index"], i)


class TestAggregateExtractions(unittest.TestCase):
    def test_empty_list(self):
        result = aggregate_extractions([])
        self.assertEqual(result, {})

    def test_single_result(self):
        data = {"requirements": [{"user_story": "Test"}], "decisions": []}
        result = aggregate_extractions([data])
        self.assertEqual(result, data)

    def test_merge_and_dedup(self):
        r1 = {
            "requirements": [{"user_story": "As a user, I want login"}],
            "decisions": [{"decision": "Use React"}],
            "action_items": [],
            "technology_stack": [],
            "emphasized_items": [],
        }
        r2 = {
            "requirements": [
                {"user_story": "As a user, I want login"},  # duplicate
                {"user_story": "As a user, I want search"},
            ],
            "decisions": [{"decision": "Use PostgreSQL"}],
            "action_items": [],
            "technology_stack": [],
            "emphasized_items": [],
        }
        result = aggregate_extractions([r1, r2])
        self.assertEqual(len(result["requirements"]), 2)  # deduped
        self.assertEqual(len(result["decisions"]), 2)

    def test_missing_categories(self):
        data = {"requirements": [{"user_story": "Test"}]}
        result = aggregate_extractions([data])
        self.assertIn("requirements", result)


class TestDedupKey(unittest.TestCase):
    def test_user_story(self):
        item = {"user_story": "As a user, I want X"}
        key = _dedup_key(item)
        self.assertIn("as a user", key)

    def test_task(self):
        item = {"task": "Fix the bug"}
        key = _dedup_key(item)
        self.assertIn("fix the bug", key)

    def test_fallback(self):
        item = {"something": "else"}
        key = _dedup_key(item)
        self.assertIsInstance(key, str)


if __name__ == "__main__":
    unittest.main()
