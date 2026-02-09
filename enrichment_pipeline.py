"Pipeline module for enriching extracted requirements with acceptance criteria and functional requirements."

import json
import os
from pathlib import Path

import anthropic

import config
from transcript_utils import (
    call_claude_with_retry,
    setup_logging,
)


def _load_prompt(prompt_filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = config.PROMPTS_DIR / prompt_filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def _load_enrichment_templates() -> dict:
    """Load the static Agile enrichment templates."""
    templates_path = config.PROMPTS_DIR / "enrichment_templates.json"
    if not templates_path.exists():
        raise FileNotFoundError(f"Enrichment templates not found: {templates_path}")
    return json.loads(templates_path.read_text(encoding="utf-8"))


def _parse_json_response(response: str, logger) -> list:
    """Parse JSON array from Claude's response."""
    text = response.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError:
        pass

    bracket_start = text.find("[")
    bracket_end = text.rfind("]")
    if bracket_start != -1 and bracket_end > bracket_start:
        try:
            data = json.loads(text[bracket_start:bracket_end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    logger.error("Failed to parse enrichment JSON response.")
    return []


def _format_enriched_requirements_doc(enriched: list) -> str:
    """Format enriched requirements into a readable Markdown document."""
    lines = ["# Enriched Requirements\n"]

    for req in enriched:
        rid = req.get("id", "REQ-???")
        lines.append(f"## {rid}\n")
        lines.append(f"**User Story:** {req.get('user_story', 'N/A')}\n")

        # Acceptance Criteria
        acs = req.get("acceptance_criteria", [])
        if acs:
            lines.append("### Acceptance Criteria\n")
            for ac in acs:
                acid = ac.get("id", "AC-??")
                lines.append(f"**{acid}:**")
                lines.append(f"- **Given** {ac.get('given', '...')}")
                lines.append(f"- **When** {ac.get('when', '...')}")
                lines.append(f"- **Then** {ac.get('then', '...')}")
                lines.append("")

        # Functional Requirements
        frs = req.get("functional_requirements", [])
        if frs:
            lines.append("### Functional Requirements\n")
            for fr in frs:
                frid = fr.get("id", "FR-??")
                lines.append(f"- **{frid}:** {fr.get('requirement', 'N/A')}")
            lines.append("")

        lines.append("---\n")

    return "\n".join(lines)


def enrich_requirements(
    requirements: list,
    model: str = None,
    logger=None,
    transcript_system_message=None,
) -> list:
    """
    Enrich extracted requirements with acceptance criteria and functional requirements.

    Uses Claude with the enrichment prompt, supplemented by static Agile templates
    for pattern guidance.

    Args:
        requirements: List of requirement dicts from extract_requirements()
        model: Claude model to use
        logger: Logger instance
        transcript_system_message: Cached transcript for context (optional)

    Returns:
        List of enriched requirement dicts with acceptance_criteria and
        functional_requirements added.
    """
    if model is None:
        model = config.DEFAULT_MODEL
    if logger is None:
        logger = setup_logging("enrich_requirements")

    if not requirements:
        logger.warning("No requirements to enrich.")
        return []

    logger.info("--- Enriching %d requirements with acceptance criteria ---", len(requirements))

    try:
        # Load prompt and templates
        prompt_template = _load_prompt(config.PROMPT_REQUIREMENTS_ENRICHMENT_FILENAME)
        templates = _load_enrichment_templates()

        # Prepare the requirements JSON for the prompt
        # Include only fields relevant for enrichment (strip source_quotes to save tokens)
        slim_reqs = []
        for req in requirements:
            slim_reqs.append({
                "id": req.get("id"),
                "user_story": req.get("user_story"),
                "role": req.get("role"),
                "capability": req.get("capability"),
                "benefit": req.get("benefit"),
                "context": req.get("context"),
            })

        requirements_json = json.dumps(slim_reqs, indent=2, ensure_ascii=False)

        # Build the prompt
        prompt = prompt_template.replace(
            "{{insert_requirements_json_here}}", requirements_json
        )

        # Append template guidance as context
        template_guidance = (
            "\n\n## Reference: Acceptance Criteria Patterns\n\n"
            "Use these Given-When-Then patterns as inspiration (adapt to the specific requirement):\n\n"
        )
        for category, patterns in templates.get("acceptance_criteria_patterns", {}).get("patterns", {}).items():
            template_guidance += f"### {category.replace('_', ' ').title()}\n"
            for p in patterns:
                template_guidance += f"- Given {p['given']}, When {p['when']}, Then {p['then']}\n"
            template_guidance += "\n"

        template_guidance += "## Reference: Functional Requirement Patterns\n\n"
        for category, pattern in templates.get("functional_requirement_patterns", {}).get("patterns", {}).items():
            template_guidance += f"- **{category.replace('_', ' ').title()}:** {pattern}\n"

        prompt += template_guidance

        # Call Claude
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
        client = anthropic.Anthropic(api_key=api_key)

        call_kwargs = {}
        if transcript_system_message:
            call_kwargs["system"] = transcript_system_message

        logger.info("Sending enrichment request to Claude (%s)...", model)
        message = call_claude_with_retry(
            client=client,
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.MAX_TOKENS_ENRICHMENT,
            temperature=config.TEMP_ANALYSIS,
            stream=True,
            min_length=100,
            timeout=config.TIMEOUT_SUMMARY,
            logger=logger,
            **call_kwargs,
        )
        response_text = message.content[0].text

        enriched = _parse_json_response(response_text, logger)

        if not enriched:
            logger.error("Enrichment returned no results.")
            return requirements  # Return originals unchanged

        # Merge enrichment back into original requirements (preserve source_quotes etc.)
        enriched_map = {item.get("id"): item for item in enriched}
        merged = []
        for req in requirements:
            rid = req.get("id")
            if rid in enriched_map:
                enrichment = enriched_map[rid]
                merged_req = {**req}
                merged_req["acceptance_criteria"] = enrichment.get("acceptance_criteria", [])
                merged_req["functional_requirements"] = enrichment.get("functional_requirements", [])
                merged.append(merged_req)
            else:
                logger.warning("Requirement %s not found in enrichment response.", rid)
                merged.append(req)

        logger.info("✓ Enriched %d requirements.", len(merged))
        return merged

    except Exception as e:
        logger.error("Error enriching requirements: %s", e, exc_info=True)
        return requirements  # Return originals on failure


def save_enriched_requirements(enriched: list, stem: str, logger=None) -> tuple:
    """
    Save enriched requirements as both JSON working file and Markdown document.

    Returns (json_path, doc_path) tuple.
    """
    if logger is None:
        logger = setup_logging("save_enriched_requirements")

    project_dir = config.PROJECTS_DIR / stem
    project_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = project_dir / f"{stem}{config.SUFFIX_ENRICHED_REQUIREMENTS}"
    json_path.write_text(
        json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("  Saved enriched JSON: %s", json_path.name)

    # Save Markdown doc
    doc_content = _format_enriched_requirements_doc(enriched)
    doc_path = project_dir / f"{stem}{config.SUFFIX_ENRICHED_REQUIREMENTS_DOC}"
    doc_path.write_text(doc_content, encoding="utf-8")
    logger.info("  Saved enriched doc: %s", doc_path.name)

    return json_path, doc_path
