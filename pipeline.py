"""
Core pipeline facade for the meeting transcript processing application.
Orchestrates the complete workflow: clean -> chunk -> extract -> enrich -> validate -> generate.
"""

from formatting_pipeline import clean_transcript
from chunking import chunk_text, needs_chunking, count_tokens, aggregate_extractions
from extraction_pipeline import extract_all
from enrichment_pipeline import enrich_requirements
from validation_pipeline import validate_extraction
from html_generator import (
    generate_markdown_report,
    generate_html_report,
    generate_pdf_report,
)
from transcript_utils import setup_logging, delete_logs

__all__ = [
    "clean_transcript",
    "chunk_text",
    "needs_chunking",
    "count_tokens",
    "aggregate_extractions",
    "extract_all",
    "enrich_requirements",
    "validate_extraction",
    "generate_markdown_report",
    "generate_html_report",
    "generate_pdf_report",
    "setup_logging",
    "delete_logs",
]
