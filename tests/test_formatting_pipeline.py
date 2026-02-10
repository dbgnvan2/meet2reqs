import re
import unittest

from formatting_pipeline import (
    _compare_transcripts,
    _generate_yaml_front_matter,
    _normalize_word_for_validation,
    strip_sic_annotations,
)


class TestFormattingPipeline(unittest.TestCase):

    def test_generate_yaml_front_matter(self):
        meta = {
            "title": "Roots of Bowen Theory",
            "presenter": "Dr Michael Kerr",
            "date": "2019-11-15",
            "year": "2019",
            "stem": "Roots of Bowen Theory - Dr Michael Kerr - 2019-11-15"
        }
        source_filename = "Roots of Bowen Theory - Dr Michael Kerr - 2019-11-15.mp4"
        
        yaml_content = _generate_yaml_front_matter(meta, source_filename)
        
        self.assertIn('Title: "Roots of Bowen Theory"', yaml_content)
        self.assertIn('Presenter: "Dr Michael Kerr"', yaml_content)
        self.assertIn('Lecture date: "2019-11-15"', yaml_content)
        self.assertIn('Source recording: "Roots of Bowen Theory - Dr Michael Kerr - 2019-11-15.mp4"', yaml_content)
        self.assertIn('License: "© 2019 Dr Michael Kerr. All rights reserved."', yaml_content)
        self.assertTrue(yaml_content.startswith("---"))
        self.assertIn("---", yaml_content[3:]) # Should end with ---

    def test_strip_sic_annotations(self):
        text = "This is a mispelled [sic] word."
        cleaned, count = strip_sic_annotations(text)
        self.assertEqual(cleaned.strip(), "This is a mispelled word.")
        self.assertEqual(count, 1)

        text_with_comment = "Another errror [sic] (spelling) here."
        cleaned, count = strip_sic_annotations(text_with_comment)
        self.assertEqual(cleaned.strip(), "Another errror here.")
        self.assertEqual(count, 1)

    def test_normalize_word_for_validation(self):
        # Basic lowercasing
        self.assertEqual(_normalize_word_for_validation("Word"), "word")
        
        # Punctuation stripping
        self.assertEqual(_normalize_word_for_validation("word."), "word")
        self.assertEqual(_normalize_word_for_validation("word,"), "word")
        self.assertEqual(_normalize_word_for_validation("?word!"), "word")
        
        # Markdown stripping
        self.assertEqual(_normalize_word_for_validation("**word**"), "word")
        self.assertEqual(_normalize_word_for_validation("*word*"), "word")
        self.assertEqual(_normalize_word_for_validation("__word__"), "word")
        self.assertEqual(_normalize_word_for_validation("`code`"), "code")

class TestSpeakerLabelStripping(unittest.TestCase):
    """Tests for speaker label stripping in format validation."""

    # Regex from validate_format for Teams/Zoom/Otter speaker labels
    SPEAKER_LABEL_RE = re.compile(
        r"^\s*[A-Z][a-zA-Z'-]+(?:\s+[A-Za-z][a-zA-Z'-]+)+\s+\d+:\d{2}(?::\d{2})?\s*$",
        re.MULTILINE,
    )

    def test_strips_two_word_name_with_timestamp(self):
        raw = "Derek Dickson  0:00\nMorning, everyone."
        cleaned = self.SPEAKER_LABEL_RE.sub("", raw)
        self.assertNotIn("Derek", cleaned)
        self.assertIn("Morning", cleaned)

    def test_strips_name_with_long_timestamp(self):
        raw = "Jane Smith  12:34:56\nLet's begin."
        cleaned = self.SPEAKER_LABEL_RE.sub("", raw)
        self.assertNotIn("Jane", cleaned)
        self.assertIn("begin", cleaned)

    def test_strips_three_word_name(self):
        raw = "Maria De Cruz  1:23\nWelcome."
        cleaned = self.SPEAKER_LABEL_RE.sub("", raw)
        self.assertNotIn("Maria", cleaned)

    def test_preserves_normal_speech(self):
        raw = "I spoke with Derek yesterday about the project."
        cleaned = self.SPEAKER_LABEL_RE.sub("", raw)
        self.assertEqual(raw, cleaned)

    def test_preserves_line_with_extra_content(self):
        raw = "Derek Dickson  0:00  said hello"
        cleaned = self.SPEAKER_LABEL_RE.sub("", raw)
        # Should NOT strip because there's content after the timestamp
        self.assertIn("Derek", cleaned)


class TestSpeakerNameExtraction(unittest.TestCase):
    """Tests for extracting speaker names from formatted bold labels."""

    def test_extracts_names_from_bold_labels(self):
        formatted = "**Derek Dickson:** Morning, everyone.\n**Olena Panfyorov:** Hello."
        names = set()
        for match in re.finditer(r"\*\*([^*:]+):\*\*", formatted):
            name = match.group(1).strip()
            if len(name) > 2:
                names.add(name)
        self.assertIn("Derek Dickson", names)
        self.assertIn("Olena Panfyorov", names)

    def test_strips_bare_speaker_names_from_raw(self):
        formatted = "**Derek Dickson:** Morning."
        raw = "Derek Dickson\nMorning, everyone."

        # Extract names
        names = set()
        for match in re.finditer(r"\*\*([^*:]+):\*\*", formatted):
            name = match.group(1).strip()
            if len(name) > 2:
                names.add(name)

        # Strip from raw
        raw_clean = raw
        for name in names:
            escaped = re.escape(name)
            raw_clean = re.sub(rf"^\s*{escaped}\s*$", "", raw_clean, flags=re.MULTILINE)

        self.assertNotIn("Derek Dickson", raw_clean)
        self.assertIn("Morning", raw_clean)

    def test_does_not_strip_inline_name_mentions(self):
        formatted = "**Derek Dickson:** Morning."
        raw = "I asked Derek Dickson about the timeline."

        names = set()
        for match in re.finditer(r"\*\*([^*:]+):\*\*", formatted):
            name = match.group(1).strip()
            if len(name) > 2:
                names.add(name)

        raw_clean = raw
        for name in names:
            escaped = re.escape(name)
            raw_clean = re.sub(rf"^\s*{escaped}\s*$", "", raw_clean, flags=re.MULTILINE)

        # Should preserve because it's inline, not a standalone line
        self.assertIn("Derek Dickson", raw_clean)


class TestCompareTranscriptsWithSpeakerLabels(unittest.TestCase):
    """Integration test: _compare_transcripts with speaker labels already stripped."""

    def test_no_mismatches_when_labels_stripped(self):
        # Simulate a cleaned raw text (speaker labels already removed)
        raw_clean = "Morning everyone. Let's discuss the project."
        formatted_clean = "Morning everyone. Let's discuss the project."
        result = _compare_transcripts(raw_clean, formatted_clean, set(), 10, 0.05, None)
        self.assertEqual(result["mismatch_count"], 0)

    def test_mismatches_from_unstripped_labels(self):
        # Simulate raw with speaker label NOT stripped
        raw_clean = "Derek Dickson Morning everyone."
        formatted_clean = "Morning everyone."
        result = _compare_transcripts(raw_clean, formatted_clean, set(), 10, 0.05, None)
        self.assertGreater(result["mismatch_count"], 0)


if __name__ == '__main__':
    unittest.main()
