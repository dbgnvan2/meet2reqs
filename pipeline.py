"""
Core pipeline logic for the transcript processing application.
This module acts as a facade, orchestrating the business logic by delegating
to specialized pipeline modules.
"""

# === meet2reqs pipeline (active) ===
from extraction_pipeline import (
    _load_formatted_transcript,
    extract_action_items,
    extract_decisions,
    extract_emphasis_points,
    extract_requirements,
    process_transcript,
)
from enrichment_pipeline import (
    enrich_requirements,
    save_enriched_requirements,
)
from formatting_pipeline import (
    add_yaml,
    format_transcript,
    validate_format,
)
from pdf_generator import generate_pdf
from packaging_pipeline import package_transcript
from transcript_utils import delete_logs, setup_logging
from validation_pipeline import (
    validate_extraction,
    validate_headers,
)

# === Legacy pipeline (backward compatibility) ===
from extraction_pipeline import (
    extract_bowen_references_from_transcript,
    extract_scored_emphasis,
    generate_structured_abstract,
    generate_structured_summary,
    summarize_transcript,
)
from validation_pipeline import (
    validate_abstract_coverage,
    validate_summary_coverage,
)
from validation_pipeline import (
    validate_abstract_legacy as validate_abstract,  # Legacy
)

# Explicitly export symbols to prevent linters from removing them
__all__ = [
    # meet2reqs pipeline
    "process_transcript",
    "extract_requirements",
    "extract_action_items",
    "extract_decisions",
    "extract_emphasis_points",
    "enrich_requirements",
    "save_enriched_requirements",
    "validate_extraction",
    "generate_pdf",
    # Shared
    "add_yaml",
    "format_transcript",
    "validate_format",
    "validate_headers",
    "_load_formatted_transcript",
    "package_transcript",
    "delete_logs",
    "setup_logging",
    # Legacy
    "extract_bowen_references_from_transcript",
    "extract_scored_emphasis",
    "generate_structured_abstract",
    "generate_structured_summary",
    "summarize_transcript",
    "validate_abstract_coverage",
    "validate_summary_coverage",
    "validate_abstract",
]
