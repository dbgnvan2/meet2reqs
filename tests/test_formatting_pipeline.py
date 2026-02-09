"""Tests for formatting_pipeline.py - cleaning and caching."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import config


class TestCleanTranscriptCaching(unittest.TestCase):
    """Tests for the cleaning pipeline's caching behavior."""

    @patch("formatting_pipeline.validate_api_key")
    @patch("formatting_pipeline.Anthropic")
    @patch("formatting_pipeline.load_prompt")
    def test_cache_hit_skips_api(self, mock_prompt, mock_anthropic, mock_key):
        """When a cached cleaned file exists, API should not be called."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # Setup source file
            source_dir = tmpdir / "source"
            source_dir.mkdir()
            raw_file = source_dir / "meeting.txt"
            raw_file.write_text("Raw transcript content")

            # Setup project dir with cached file
            project_dir = tmpdir / "projects" / "meeting"
            project_dir.mkdir(parents=True)
            cleaned_file = project_dir / f"meeting{config.SUFFIX_CLEANED}"
            cleaned_file.write_text("Cached cleaned content")

            # Patch config paths
            with patch.object(config, "SOURCE_DIR", source_dir), \
                 patch.object(config, "PROJECTS_DIR", tmpdir / "projects"), \
                 patch("formatting_pipeline.config.SOURCE_DIR", source_dir), \
                 patch("formatting_pipeline.ensure_project_dir", return_value=project_dir):

                from formatting_pipeline import clean_transcript
                result = clean_transcript("meeting.txt")

                self.assertTrue(result["from_cache"])
                self.assertEqual(result["cleaned_text"], "Cached cleaned content")
                self.assertEqual(result["input_tokens"], 0)
                mock_anthropic.assert_not_called()


class TestCleanTranscriptInput(unittest.TestCase):
    """Tests for input validation."""

    def test_missing_file_raises(self):
        from formatting_pipeline import clean_transcript
        with self.assertRaises(FileNotFoundError):
            clean_transcript("nonexistent_file.txt")


if __name__ == "__main__":
    unittest.main()
