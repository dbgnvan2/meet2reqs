"""Tests for pipeline.py - facade import verification."""

import unittest


class TestPipelineImports(unittest.TestCase):
    """Verify that the pipeline facade exports all expected functions."""

    def test_clean_transcript(self):
        from pipeline import clean_transcript
        self.assertTrue(callable(clean_transcript))

    def test_extract_all(self):
        from pipeline import extract_all
        self.assertTrue(callable(extract_all))

    def test_enrich_requirements(self):
        from pipeline import enrich_requirements
        self.assertTrue(callable(enrich_requirements))

    def test_validate_extraction(self):
        from pipeline import validate_extraction
        self.assertTrue(callable(validate_extraction))

    def test_generate_markdown_report(self):
        from pipeline import generate_markdown_report
        self.assertTrue(callable(generate_markdown_report))

    def test_generate_html_report(self):
        from pipeline import generate_html_report
        self.assertTrue(callable(generate_html_report))

    def test_generate_pdf_report(self):
        from pipeline import generate_pdf_report
        self.assertTrue(callable(generate_pdf_report))

    def test_chunking_functions(self):
        from pipeline import chunk_text, needs_chunking, count_tokens, aggregate_extractions
        self.assertTrue(callable(chunk_text))
        self.assertTrue(callable(needs_chunking))
        self.assertTrue(callable(count_tokens))
        self.assertTrue(callable(aggregate_extractions))

    def test_setup_logging(self):
        from pipeline import setup_logging
        self.assertTrue(callable(setup_logging))


if __name__ == "__main__":
    unittest.main()
