#!/usr/bin/env python3
"""
Interactive Meeting Transcript Processing Pipeline (CLI)

Guides user through the complete workflow:
1. Select source file
2. Clean and format transcript
3. Extract requirements, decisions, action items, tech stack, emphasis
4. Enrich requirements with acceptance criteria
5. Validate extraction quality
6. Generate reports (Markdown, HTML, PDF)
7. Move source to processed/

Usage:
    python transcript_process.py
"""

import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import config
from transcript_utils import setup_logging, validate_api_key


def list_source_files():
    """List available transcript files in source directory."""
    source_dir = config.SOURCE_DIR
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        return []

    files = sorted(
        [f for f in source_dir.iterdir() if f.is_file() and not f.name.startswith(".")],
        key=lambda f: f.name,
    )
    return files


def display_files(files):
    """Display numbered list of files."""
    if not files:
        print("No transcript files found in source directory.")
        return
    print("\nAvailable transcripts:")
    print("-" * 60)
    for i, f in enumerate(files, 1):
        size = f.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} B"
        print(f"  {i}. {f.name}  ({size_str})")
    print()


def get_user_choice(files):
    """Get user's file selection."""
    while True:
        try:
            choice = input("Select a file (number) or 'q' to quit: ").strip()
            if choice.lower() == "q":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return files[idx]
            print(f"Invalid selection. Choose 1-{len(files)}.")
        except ValueError:
            print("Enter a number or 'q'.")


def confirm(prompt: str) -> bool:
    """Ask user for confirmation."""
    response = input(f"{prompt} (y/n): ").strip().lower()
    return response in ("y", "yes")


def main():
    """Run the interactive pipeline."""
    print("=" * 60)
    print("  Meeting Transcript Processor")
    print("  Extract requirements, decisions, and action items")
    print("=" * 60)

    # Validate setup
    try:
        validate_api_key()
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # List and select file
    files = list_source_files()
    if not files:
        print("\nNo files found. Place transcript files in:", config.SOURCE_DIR)
        sys.exit(0)

    display_files(files)
    selected = get_user_choice(files)
    if not selected:
        print("Goodbye.")
        return

    raw_filename = selected.name
    logger = setup_logging("transcript_process")
    logger.info("Selected: %s", raw_filename)

    # Step 1: Clean
    print("\n--- Step 1: Clean and Format Transcript ---")
    from formatting_pipeline import clean_transcript
    result = clean_transcript(raw_filename, logger=logger)
    base_name = result["base_name"]

    if result["from_cache"]:
        print(f"  Using cached cleaned transcript ({result['token_count']} tokens)")
    else:
        print(f"  Cleaned: {result['token_count']} tokens (API: {result['input_tokens']} in, {result['output_tokens']} out)")

    # Step 2: Extract
    print("\n--- Step 2: Extract All Categories ---")
    from extraction_pipeline import extract_all
    extraction = extract_all(result["cleaned_text"], base_name, logger=logger)
    for cat in config.EXTRACTION_CATEGORIES:
        print(f"  {cat}: {len(extraction.get(cat, []))} items")

    # Step 3: Enrich
    print("\n--- Step 3: Enrich Requirements ---")
    requirements = extraction.get("requirements", [])
    enriched = []
    if requirements:
        from enrichment_pipeline import enrich_requirements
        enriched = enrich_requirements(requirements, base_name, logger=logger)
        print(f"  Enriched {len(enriched)} requirements")
        ambiguous = sum(1 for r in enriched if r.get("confidence") == "low")
        if ambiguous:
            print(f"  Warning: {ambiguous} requirement(s) flagged for manual review")
    else:
        print("  No requirements to enrich.")

    # Step 4: Validate
    print("\n--- Step 4: Validate Extraction ---")
    from validation_pipeline import validate_extraction
    report = validate_extraction(
        extraction, result["cleaned_text"], base_name,
        enriched_requirements=enriched, logger=logger,
    )
    score = report.get("overall_score", 0)
    print(f"  Validation score: {score:.0%}")
    if score < config.MIN_COVERAGE_SCORE:
        print(f"  Warning: Below minimum coverage threshold ({config.MIN_COVERAGE_SCORE:.0%})")
        if not confirm("  Continue with report generation?"):
            print("  Stopping. Review validation report and re-run.")
            return

    # Step 5: Generate Reports
    print("\n--- Step 5: Generate Reports ---")
    from html_generator import generate_markdown_report, generate_html_report, generate_pdf_report

    generate_markdown_report(extraction, enriched, base_name, report, logger)
    print("  Generated Markdown report")

    generate_html_report(extraction, enriched, base_name, report, logger)
    print("  Generated HTML report")

    pdf_path = generate_pdf_report(extraction, enriched, base_name, report, logger)
    if pdf_path:
        print(f"  Generated PDF report")
    else:
        print("  PDF generation skipped (WeasyPrint not available)")

    # Step 6: Archive
    if confirm("\nMove source file to processed/?"):
        processed_dir = config.PROCESSED_DIR
        processed_dir.mkdir(parents=True, exist_ok=True)
        dest = processed_dir / raw_filename
        shutil.move(str(selected), str(dest))
        print(f"  Moved to: {dest}")

    print(f"\nDone! Outputs saved to: {config.PROJECTS_DIR / base_name}")


if __name__ == "__main__":
    main()
