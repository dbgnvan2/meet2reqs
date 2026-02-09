"""
Enrichment pipeline for user story requirements.
Requirement 4: Add acceptance criteria (Given-When-Then) and functional
requirements to each extracted user story.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

import config
from transcript_utils import (
    call_claude_with_retry,
    create_system_message_with_cache,
    ensure_project_dir,
    load_prompt,
    validate_api_key,
)

load_dotenv()


def enrich_requirements(
    requirements: list[dict],
    base_name: str,
    model: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> list[dict]:
    """
    Enrich extracted user stories with acceptance criteria and functional requirements.

    For each user story, adds:
    - 3-5 acceptance criteria in Given-When-Then format
    - Functional requirements (system behaviors)
    - Confidence flag for ambiguous stories

    Args:
        requirements: List of requirement dicts from extraction
        base_name: Project base name for saving output
        model: Override enrichment model
        logger: Logger instance

    Returns:
        List of enriched requirement dicts
    """
    model = model or config.settings.ENRICHMENT_MODEL

    if not requirements:
        if logger:
            logger.info("No requirements to enrich.")
        return []

    prompt_text = load_prompt(config.PROMPT_ENRICHMENT_FILENAME)
    api_key = validate_api_key()
    client = Anthropic(api_key=api_key)

    # Send all requirements in one call for efficiency
    requirements_json = json.dumps(requirements, indent=2, ensure_ascii=False)
    system_msg = create_system_message_with_cache(prompt_text)
    messages = [{"role": "user", "content": requirements_json}]

    if logger:
        logger.info("Enriching %d requirements with %s...", len(requirements), model)

    message = call_claude_with_retry(
        client=client,
        model=model,
        messages=messages,
        max_tokens=config.MAX_TOKENS_ENRICHMENT,
        temperature=config.TEMP_ANALYSIS,
        logger=logger,
        min_length=100,
        system=system_msg,
        timeout=config.TIMEOUT_ENRICHMENT,
    )

    response_text = message.content[0].text
    enriched = _parse_enrichment_response(response_text, requirements, logger)

    # Save enriched output
    project_dir = ensure_project_dir(base_name)
    output_path = project_dir / f"{base_name}{config.SUFFIX_ENRICHED}"
    output_path.write_text(
        json.dumps(enriched, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if logger:
        logger.info("Saved enriched requirements: %s", output_path.name)
        ambiguous = sum(1 for r in enriched if r.get("confidence") == "low")
        if ambiguous:
            logger.warning("%d requirement(s) flagged as ambiguous for manual review.", ambiguous)

    return enriched


def _parse_enrichment_response(
    response_text: str,
    original_requirements: list[dict],
    logger: Optional[logging.Logger] = None,
) -> list[dict]:
    """Parse enrichment response JSON. Falls back to original requirements on failure."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        enriched = json.loads(text)
        if not isinstance(enriched, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        if logger:
            logger.error("Failed to parse enrichment JSON: %s", e)
        # Return originals with empty enrichment fields
        return [
            {**req, "acceptance_criteria": [], "functional_requirements": [], "confidence": "low"}
            for req in original_requirements
        ]

    # Ensure each item has the expected fields
    for item in enriched:
        if "acceptance_criteria" not in item:
            item["acceptance_criteria"] = []
        if "functional_requirements" not in item:
            item["functional_requirements"] = []
        if "confidence" not in item:
            item["confidence"] = "medium"

    return enriched
