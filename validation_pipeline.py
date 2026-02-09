"""
Validation pipeline for extracted and enriched meeting transcript data.
Requirement 5: Multi-level validation for all extraction categories.
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
    find_text_in_content,
    load_prompt,
    validate_api_key,
)

load_dotenv()


def validate_extraction(
    extraction: dict,
    cleaned_text: str,
    base_name: str,
    enriched_requirements: Optional[list[dict]] = None,
    model: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Run multi-level validation on extracted and enriched data.

    Validation levels:
    1. Structure: JSON schema compliance for each category
    2. Fidelity: Decisions/emphasized items traced back to transcript
    3. Completeness: Coverage check via LLM
    4. Requirements quality: INVEST compliance and testability
    5. Enrichment quality: Acceptance criteria have clear outcomes

    Returns:
        Validation report dict with per-category results and overall score
    """
    model = model or config.settings.VALIDATION_MODEL
    report = {"categories": {}, "overall_score": 0.0, "issues": []}

    # Level 1: Structure validation
    for category in config.EXTRACTION_CATEGORIES:
        items = extraction.get(category, [])
        cat_report = _validate_structure(category, items, logger)
        report["categories"][category] = cat_report

    # Level 2: Fidelity -- check that extracted items trace to transcript
    fidelity_results = _validate_fidelity(extraction, cleaned_text, logger)
    for category, result in fidelity_results.items():
        report["categories"][category]["fidelity"] = result

    # Level 3: Requirements quality (INVEST compliance)
    requirements = extraction.get("requirements", [])
    if requirements:
        invest_results = _validate_invest(requirements, logger)
        report["categories"]["requirements"]["invest"] = invest_results

    # Level 4: Enrichment quality
    if enriched_requirements:
        enrichment_results = _validate_enrichment(enriched_requirements, logger)
        report["categories"]["requirements"]["enrichment"] = enrichment_results

    # Level 5: Completeness via LLM
    completeness = _validate_completeness(extraction, cleaned_text, model, logger)
    report["completeness"] = completeness

    # Calculate overall score
    report["overall_score"] = _calculate_score(report)

    # Save report
    project_dir = ensure_project_dir(base_name)
    report_path = project_dir / f"{base_name}{config.SUFFIX_VALIDATION_REPORT}"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if logger:
        logger.info(
            "Validation complete. Score: %.1f%%. Report: %s",
            report["overall_score"] * 100, report_path.name,
        )

    return report


def _validate_structure(
    category: str, items: list, logger: Optional[logging.Logger] = None
) -> dict:
    """Validate JSON structure for a category."""
    result = {"count": len(items), "valid": 0, "issues": []}

    required_fields = {
        "requirements": ["user_story"],
        "decisions": ["decision", "rationale"],
        "action_items": ["task"],
        "technology_stack": ["name"],
        "emphasized_items": ["phrase"],
    }

    fields = required_fields.get(category, [])
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            result["issues"].append(f"Item {i}: not a dict")
            continue
        missing = [f for f in fields if f not in item or not item[f]]
        if missing:
            result["issues"].append(f"Item {i}: missing fields {missing}")
        else:
            result["valid"] += 1

    if logger and result["issues"]:
        logger.warning("Structure issues in %s: %d", category, len(result["issues"]))

    return result


def _validate_fidelity(
    extraction: dict,
    cleaned_text: str,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """Check that extracted items can be traced back to the transcript."""
    results = {}

    # Check decisions have verbatim or near-verbatim support
    decisions = extraction.get("decisions", [])
    decision_fidelity = {"checked": 0, "found": 0, "missing": []}
    for dec in decisions:
        text_to_find = dec.get("decision", "")
        if not text_to_find:
            continue
        decision_fidelity["checked"] += 1
        _, _, ratio = find_text_in_content(text_to_find, cleaned_text, aggressive_normalization=True)
        if ratio >= config.FUZZY_MATCH_THRESHOLD:
            decision_fidelity["found"] += 1
        else:
            decision_fidelity["missing"].append(text_to_find[:80])
    results["decisions"] = decision_fidelity

    # Check emphasized items
    emphasis = extraction.get("emphasized_items", [])
    emphasis_fidelity = {"checked": 0, "found": 0, "missing": []}
    for item in emphasis:
        text_to_find = item.get("phrase", "") or item.get("quote", "")
        if not text_to_find:
            continue
        emphasis_fidelity["checked"] += 1
        _, _, ratio = find_text_in_content(text_to_find, cleaned_text, aggressive_normalization=True)
        if ratio >= config.FUZZY_MATCH_THRESHOLD:
            emphasis_fidelity["found"] += 1
        else:
            emphasis_fidelity["missing"].append(text_to_find[:80])
    results["emphasized_items"] = emphasis_fidelity

    if logger:
        for cat, fid in results.items():
            if fid["checked"] > 0:
                logger.info(
                    "Fidelity %s: %d/%d found (%.0f%%)",
                    cat, fid["found"], fid["checked"],
                    fid["found"] / fid["checked"] * 100 if fid["checked"] else 0,
                )

    return results


def _validate_invest(
    requirements: list[dict], logger: Optional[logging.Logger] = None
) -> dict:
    """Check if user stories follow INVEST principles."""
    result = {"checked": 0, "compliant": 0, "issues": []}

    for i, req in enumerate(requirements):
        story = req.get("user_story", "")
        if not story:
            continue
        result["checked"] += 1
        issues = []

        # Check user story format: "As a [role], I want [feature] so that [benefit]"
        story_lower = story.lower()
        if not story_lower.startswith("as a "):
            issues.append("Missing 'As a [role]' prefix")
        if "i want" not in story_lower and "i need" not in story_lower:
            issues.append("Missing 'I want/need [feature]' clause")
        if "so that" not in story_lower and "in order to" not in story_lower:
            issues.append("Missing 'so that [benefit]' clause")

        if issues:
            result["issues"].append({"index": i, "story": story[:80], "issues": issues})
        else:
            result["compliant"] += 1

    if logger:
        logger.info(
            "INVEST compliance: %d/%d stories compliant",
            result["compliant"], result["checked"],
        )

    return result


def _validate_enrichment(
    enriched: list[dict], logger: Optional[logging.Logger] = None
) -> dict:
    """Validate enrichment quality: acceptance criteria have clear outcomes."""
    result = {"checked": 0, "good": 0, "issues": []}

    for i, req in enumerate(enriched):
        ac_list = req.get("acceptance_criteria", [])
        if not ac_list:
            result["issues"].append({"index": i, "issue": "No acceptance criteria"})
            continue

        result["checked"] += 1
        has_given_when_then = False
        for ac in ac_list:
            ac_lower = ac.lower() if isinstance(ac, str) else ""
            if "given" in ac_lower and "when" in ac_lower and "then" in ac_lower:
                has_given_when_then = True
                break

        if has_given_when_then:
            result["good"] += 1
        else:
            result["issues"].append({
                "index": i,
                "issue": "No Given-When-Then format found",
            })

    if logger:
        logger.info(
            "Enrichment quality: %d/%d with proper GWT format",
            result["good"], result["checked"],
        )

    return result


def _validate_completeness(
    extraction: dict,
    cleaned_text: str,
    model: str,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """Use LLM to check extraction completeness against transcript."""
    prompt_text = load_prompt(config.PROMPT_VALIDATION_FILENAME)
    api_key = validate_api_key()
    client = Anthropic(api_key=api_key)

    # Build a summary of what was extracted
    summary_parts = []
    for category in config.EXTRACTION_CATEGORIES:
        items = extraction.get(category, [])
        summary_parts.append(f"## {category} ({len(items)} items)")
        for item in items[:10]:  # Limit to first 10 per category
            if isinstance(item, dict):
                label = item.get("user_story") or item.get("decision") or item.get("task") or item.get("name") or item.get("phrase") or str(item)
                summary_parts.append(f"- {label[:120]}")
            else:
                summary_parts.append(f"- {str(item)[:120]}")

    extraction_summary = "\n".join(summary_parts)

    system_msg = create_system_message_with_cache(prompt_text)
    user_content = (
        f"## Transcript\n{cleaned_text}\n\n"
        f"## Extracted Items\n{extraction_summary}"
    )
    messages = [{"role": "user", "content": user_content}]

    try:
        message = call_claude_with_retry(
            client=client,
            model=model,
            messages=messages,
            max_tokens=config.MAX_TOKENS_VALIDATION,
            temperature=config.TEMP_STRICT,
            logger=logger,
            min_length=20,
            system=system_msg,
            timeout=config.TIMEOUT_VALIDATION,
        )
        response_text = message.content[0].text

        # Try to parse JSON response
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_response": response_text, "score": 0.0}

    except Exception as e:
        if logger:
            logger.error("Completeness validation failed: %s", e)
        return {"error": str(e), "score": 0.0}


def _calculate_score(report: dict) -> float:
    """Calculate overall validation score (0.0 to 1.0)."""
    scores = []

    # Structure scores
    for category, cat_report in report.get("categories", {}).items():
        total = cat_report.get("count", 0)
        valid = cat_report.get("valid", 0)
        if total > 0:
            scores.append(valid / total)

    # Fidelity scores
    for category, cat_report in report.get("categories", {}).items():
        fid = cat_report.get("fidelity", {})
        if isinstance(fid, dict) and fid.get("checked", 0) > 0:
            scores.append(fid["found"] / fid["checked"])

    # INVEST score
    invest = report.get("categories", {}).get("requirements", {}).get("invest", {})
    if invest.get("checked", 0) > 0:
        scores.append(invest["compliant"] / invest["checked"])

    # Completeness score
    completeness = report.get("completeness", {})
    if isinstance(completeness, dict) and "score" in completeness:
        try:
            scores.append(float(completeness["score"]))
        except (ValueError, TypeError):
            pass

    return sum(scores) / len(scores) if scores else 0.0
