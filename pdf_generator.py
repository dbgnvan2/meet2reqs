"PDF generation for meet2reqs extraction outputs."

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config
from transcript_utils import (
    extract_section,
    markdown_to_html,
    parse_filename_metadata,
    setup_logging,
    strip_yaml_frontmatter,
    validate_input_file,
)

# Jinja2 setup
TEMPLATES_DIR = Path(__file__).parent / "templates"
STYLES_DIR = TEMPLATES_DIR / "styles"

template_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _load_css(filename: str) -> str:
    """Load a CSS file from the styles directory."""
    css_path = STYLES_DIR / filename
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


COMMON_CSS = _load_css("common.css")
PDF_CSS = _load_css("pdf.css")


def _load_json_file(path: Path) -> list:
    """Load a JSON file, returning empty list on failure."""
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def generate_pdf(
    base_name: str,
    extraction_results: dict = None,
    logger=None,
) -> bool:
    """
    Generate a PDF document from meet2reqs extraction results.

    Args:
        base_name: Project stem name
        extraction_results: Dict from process_transcript(). If None, loads from files.
        logger: Logger instance

    Returns:
        True on success, False on failure.
    """
    if logger is None:
        logger = setup_logging("generate_pdf")

    try:
        from weasyprint import HTML
    except ImportError:
        logger.error(
            "WeasyPrint is not installed. Install with: pip install weasyprint"
        )
        return False

    try:
        project_dir = config.PROJECTS_DIR / base_name
        output_file = project_dir / f"{base_name}{config.SUFFIX_PDF}"

        # Build metadata
        metadata = parse_filename_metadata(base_name)
        meta = {
            "title": metadata.get("title", base_name),
            "author": metadata.get("author", ""),
            "date": metadata.get("date", ""),
        }

        # Load extraction results from files if not provided
        if extraction_results is None:
            extraction_results = {}
            for key, suffix in [
                ("requirements", config.SUFFIX_REQUIREMENTS),
                ("action_items", config.SUFFIX_ACTION_ITEMS),
                ("decisions", config.SUFFIX_DECISIONS),
                ("emphasis_points", config.SUFFIX_EMPHASIS_POINTS),
                ("enriched_requirements", config.SUFFIX_ENRICHED_REQUIREMENTS),
            ]:
                extraction_results[key] = _load_json_file(
                    project_dir / f"{base_name}{suffix}"
                )

            # Load validation report
            val_path = project_dir / f"{base_name} - extraction-validation.json"
            if val_path.exists():
                try:
                    extraction_results["validation"] = json.loads(
                        val_path.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    extraction_results["validation"] = None

        # Load topics
        topics_html = ""
        key_items_file = project_dir / f"{base_name}{config.SUFFIX_KEY_ITEMS_ALL}"
        if key_items_file.exists():
            content = strip_yaml_frontmatter(
                key_items_file.read_text(encoding="utf-8")
            )
            topics = extract_section(content, "Topics")
            if topics:
                topics_html = markdown_to_html(topics)

        # Render template
        template = template_env.get_template("meet2reqs_pdf.html")
        html_content = template.render(
            meta=meta,
            common_css=COMMON_CSS,
            pdf_css=PDF_CSS,
            topics=bool(topics_html),
            topics_html=topics_html,
            requirements=extraction_results.get("requirements", []),
            enriched_requirements=extraction_results.get("enriched_requirements", []),
            action_items=extraction_results.get("action_items", []),
            decisions=extraction_results.get("decisions", []),
            emphasis_points=extraction_results.get("emphasis_points", []),
            validation=extraction_results.get("validation"),
        )

        # Generate PDF
        logger.info("Generating PDF with WeasyPrint...")
        HTML(string=html_content).write_pdf(output_file)
        logger.info("PDF generated: %s", output_file)
        return True

    except Exception as e:
        logger.error("Error generating PDF: %s", e, exc_info=True)
        return False
