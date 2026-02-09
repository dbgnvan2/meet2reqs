"""
Multi-output extraction pipeline for meeting transcripts.
Requirement 3: Extract requirements, decisions, action items, tech stack,
and emphasized items in a single LLM call per chunk.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

import config
from chunking import aggregate_extractions, chunk_text, needs_chunking
from transcript_utils import (
    call_claude_with_retry,
    create_system_message_with_cache,
    ensure_project_dir,
    load_prompt,
    validate_api_key,
)

load_dotenv()


def extract_all(
    cleaned_text: str,
    base_name: str,
    model: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Extract all categories from cleaned transcript text.
    If text exceeds chunk threshold, chunks and aggregates results.

    Args:
        cleaned_text: The cleaned transcript text
        base_name: Project base name for saving output files
        model: Override extraction model
        logger: Logger instance

    Returns:
        dict with keys matching config.EXTRACTION_CATEGORIES, each containing a list
    """
    model = model or config.settings.EXTRACTION_MODEL

    if needs_chunking(cleaned_text):
        if logger:
            logger.info("Transcript exceeds chunk threshold, splitting into chunks...")
        chunks = chunk_text(cleaned_text, logger=logger)
        chunk_results = []
        for chunk in chunks:
            if logger:
                logger.info("Extracting from chunk %d/%d (%d tokens)...", chunk["index"] + 1, len(chunks), chunk["tokens"])
            result = _extract_from_text(chunk["text"], model, logger)
            chunk_results.append(result)
        extraction = aggregate_extractions(chunk_results, logger=logger)
    else:
        extraction = _extract_from_text(cleaned_text, model, logger)

    # Save individual category files
    project_dir = ensure_project_dir(base_name)
    _save_extraction_files(extraction, base_name, project_dir, logger)

    return extraction


def _extract_from_text(
    text: str,
    model: str,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Single API call to extract all five categories from text.
    Returns parsed JSON dict with extraction categories.
    """
    prompt_text = load_prompt(config.PROMPT_EXTRACTION_FILENAME)
    api_key = validate_api_key()
    client = Anthropic(api_key=api_key)

    system_msg = create_system_message_with_cache(prompt_text)
    messages = [{"role": "user", "content": text}]

    message = call_claude_with_retry(
        client=client,
        model=model,
        messages=messages,
        max_tokens=config.MAX_TOKENS_EXTRACTION,
        temperature=config.TEMP_ANALYSIS,
        logger=logger,
        min_length=100,
        system=system_msg,
        timeout=config.TIMEOUT_EXTRACTION,
    )

    response_text = message.content[0].text
    return _parse_extraction_response(response_text, logger)


def _parse_extraction_response(response_text: str, logger: Optional[logging.Logger] = None) -> dict:
    """Parse the JSON extraction response, handling common issues."""
    # Strip markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        if logger:
            logger.error("Failed to parse extraction JSON: %s", e)
            logger.debug("Response text: %s", text[:500])
        # Return empty structure
        return {cat: [] for cat in config.EXTRACTION_CATEGORIES}

    # Ensure all expected categories exist
    result = {}
    for category in config.EXTRACTION_CATEGORIES:
        result[category] = data.get(category, [])
        if not isinstance(result[category], list):
            result[category] = []

    return result


def _save_extraction_files(
    extraction: dict,
    base_name: str,
    project_dir: Path,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Save each extraction category to its own JSON file."""
    suffix_map = {
        "requirements": config.SUFFIX_REQUIREMENTS,
        "decisions": config.SUFFIX_DECISIONS,
        "action_items": config.SUFFIX_ACTION_ITEMS,
        "technology_stack": config.SUFFIX_TECH_STACK,
        "emphasized_items": config.SUFFIX_EMPHASIZED,
    }

    for category, suffix in suffix_map.items():
        items = extraction.get(category, [])
        output_path = project_dir / f"{base_name}{suffix}"
        output_path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if logger:
            logger.info("Saved %s: %d items -> %s", category, len(items), output_path.name)
