"""
Document generation for meeting transcript extraction results.
Requirement 6: Generate Markdown, HTML, and PDF outputs.
"""

import json
import logging
from html import escape
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from transcript_utils import ensure_project_dir


def generate_markdown_report(
    extraction: dict,
    enriched_requirements: list[dict],
    base_name: str,
    validation_report: Optional[dict] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Generate a Markdown report from extraction results."""
    project_dir = ensure_project_dir(base_name)
    lines = [f"# Meeting Report: {base_name}\n"]

    # Requirements
    requirements = enriched_requirements or extraction.get("requirements", [])
    if requirements:
        lines.append("## Requirements\n")
        for i, req in enumerate(requirements, 1):
            story = req.get("user_story", "No user story")
            priority = req.get("priority", "medium")
            lines.append(f"### R{i}: {story}")
            lines.append(f"**Priority:** {priority}\n")

            ac = req.get("acceptance_criteria", [])
            if ac:
                lines.append("**Acceptance Criteria:**")
                for criterion in ac:
                    lines.append(f"- {criterion}")
                lines.append("")

            fr = req.get("functional_requirements", [])
            if fr:
                lines.append("**Functional Requirements:**")
                for func_req in fr:
                    lines.append(f"- {func_req}")
                lines.append("")

    # Decisions
    decisions = extraction.get("decisions", [])
    if decisions:
        lines.append("## Decisions\n")
        for i, dec in enumerate(decisions, 1):
            lines.append(f"### D{i}: {dec.get('decision', 'N/A')}")
            lines.append(f"**Rationale:** {dec.get('rationale', 'N/A')}")
            status = dec.get("status", "final")
            lines.append(f"**Status:** {status}\n")

    # Action Items
    action_items = extraction.get("action_items", [])
    if action_items:
        lines.append("## Action Items\n")
        lines.append("| # | Task | Assignee | Deadline |")
        lines.append("|---|------|----------|----------|")
        for i, item in enumerate(action_items, 1):
            task = item.get("task", "N/A")
            assignee = item.get("assignee", "Unassigned")
            deadline = item.get("deadline") or "TBD"
            lines.append(f"| {i} | {task} | {assignee} | {deadline} |")
        lines.append("")

    # Technology Stack
    tech = extraction.get("technology_stack", [])
    if tech:
        lines.append("## Technology Stack\n")
        for item in tech:
            name = item.get("name", "N/A")
            category = item.get("category", "other")
            context = item.get("context", "")
            lines.append(f"- **{name}** ({category}): {context}")
        lines.append("")

    # Emphasized Items
    emphasis = extraction.get("emphasized_items", [])
    if emphasis:
        lines.append("## Emphasized Items\n")
        for item in emphasis:
            phrase = item.get("phrase", "N/A")
            speaker = item.get("speaker", "Unknown")
            lines.append(f"- *\"{phrase}\"* -- {speaker}")
        lines.append("")

    # Validation Summary
    if validation_report:
        score = validation_report.get("overall_score", 0)
        lines.append(f"## Validation\n")
        lines.append(f"**Overall Score:** {score:.0%}\n")

    md_content = "\n".join(lines)

    output_path = project_dir / f"{base_name}{config.SUFFIX_REPORT_MD}"
    output_path.write_text(md_content, encoding="utf-8")
    if logger:
        logger.info("Generated Markdown report: %s", output_path.name)

    return md_content


def generate_html_report(
    extraction: dict,
    enriched_requirements: list[dict],
    base_name: str,
    validation_report: Optional[dict] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Generate an HTML report from extraction results."""
    project_dir = ensure_project_dir(base_name)

    env = Environment(
        loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")

    requirements = enriched_requirements or extraction.get("requirements", [])

    context = {
        "title": base_name.replace("-", " ").replace("_", " ").title(),
        "base_name": base_name,
        "requirements": requirements,
        "decisions": extraction.get("decisions", []),
        "action_items": extraction.get("action_items", []),
        "technology_stack": extraction.get("technology_stack", []),
        "emphasized_items": extraction.get("emphasized_items", []),
        "validation_score": validation_report.get("overall_score", 0) if validation_report else None,
    }

    html_content = template.render(**context)

    output_path = project_dir / f"{base_name}{config.SUFFIX_REPORT_HTML}"
    output_path.write_text(html_content, encoding="utf-8")
    if logger:
        logger.info("Generated HTML report: %s", output_path.name)

    return html_content


def generate_pdf_report(
    extraction: dict,
    enriched_requirements: list[dict],
    base_name: str,
    validation_report: Optional[dict] = None,
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """Generate a PDF report from extraction results."""
    project_dir = ensure_project_dir(base_name)

    env = Environment(
        loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("pdf.html")

    requirements = enriched_requirements or extraction.get("requirements", [])

    # Load CSS
    css_path = config.TEMPLATES_DIR / "styles" / "pdf.css"
    css_content = ""
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")

    context = {
        "title": base_name.replace("-", " ").replace("_", " ").title(),
        "base_name": base_name,
        "requirements": requirements,
        "decisions": extraction.get("decisions", []),
        "action_items": extraction.get("action_items", []),
        "technology_stack": extraction.get("technology_stack", []),
        "emphasized_items": extraction.get("emphasized_items", []),
        "validation_score": validation_report.get("overall_score", 0) if validation_report else None,
        "css": css_content,
    }

    html_content = template.render(**context)
    output_path = project_dir / f"{base_name}{config.SUFFIX_REPORT_PDF}"

    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(str(output_path))
        if logger:
            logger.info("Generated PDF report: %s", output_path.name)
        return str(output_path)
    except ImportError:
        if logger:
            logger.warning("WeasyPrint not available. Saving HTML for PDF instead.")
        html_fallback = project_dir / f"{base_name} - pdf-ready.html"
        html_fallback.write_text(html_content, encoding="utf-8")
        return str(html_fallback)
    except Exception as e:
        if logger:
            logger.error("PDF generation failed: %s", e)
        return None
