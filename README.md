# meet2reqs - Meeting Transcript Processor

A pipeline that processes meeting transcripts into structured, actionable outputs: **requirements** (user stories with acceptance criteria), **decisions**, **action items**, **technology stack**, and **emphasized items**.

Uses Anthropic's Claude API with token-efficient caching, chunking, and multi-task prompting.

[![Tests](https://img.shields.io/badge/Tests-127%20passing-brightgreen)]()

## Features

- **Cleaning & Caching**: Single LLM call cleans raw transcripts; cached output avoids redundant API calls
- **Smart Chunking**: Long transcripts automatically split at natural boundaries with configurable overlap
- **Multi-Output Extraction**: One API call extracts all five categories into structured JSON
- **Requirement Enrichment**: User stories automatically enriched with Given-When-Then acceptance criteria and functional requirements (INVEST-compliant)
- **Multi-Level Validation**: Structure, fidelity, INVEST compliance, enrichment quality, and LLM-based completeness checks
- **Triple-Format Output**: Markdown, HTML (navigable with sections), and PDF (print-ready with TOC)
- **Dual Interface**: Tkinter GUI and interactive CLI
- **Security**: Path traversal protection, XSS prevention via Jinja2 auto-escaping, API keys via environment variables

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Place transcript files in source/
mkdir -p source
cp your-meeting-transcript.txt source/

# Run the CLI
python transcript_process.py

# Or use the GUI
python transcript_processor_gui.py
```

## Pipeline Workflow

```
Raw Transcript (source/)
  1. clean_transcript()     -> cleaned.md (cached)
  2. chunk_if_needed()      -> chunks[] (if > 10K tokens)
  3. extract_all()          -> requirements.json, decisions.json, action_items.json,
                               tech_stack.json, emphasized_items.json
  4. enrich_requirements()  -> enriched_requirements.json
  5. validate_extraction()  -> validation_report.json
  6. generate_reports()     -> report.md, report.html, report.pdf
```

## Output Structure

Each processed transcript produces a project folder in `projects/<name>/` containing:

| File | Description |
|------|-------------|
| `*- cleaned.md` | Cleaned, formatted transcript |
| `*- requirements.json` | User stories extracted from discussion |
| `*- decisions.json` | Decisions with rationale and status |
| `*- action_items.json` | Tasks with assignees and deadlines |
| `*- tech_stack.json` | Technologies mentioned with context |
| `*- emphasized_items.json` | Key phrases and strong statements |
| `*- enriched_requirements.json` | Requirements with acceptance criteria |
| `*- validation_report.json` | Quality and completeness scores |
| `*- report.md` | Full Markdown report |
| `*- report.html` | Navigable HTML report |
| `*- report.pdf` | Print-ready PDF report |

## Development

```bash
# Run tests
pytest tests/

# Lint and format
ruff check .
ruff format .

# Validate configuration
python -c "import config; config.validate_or_exit()"
```

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `CACHE_CLEANED` | `True` | Cache cleaned transcripts to avoid redundant API calls |
| `CHUNK_THRESHOLD` | `10000` | Token count before chunking kicks in |
| `CHUNK_MAX_TOKENS` | `4000` | Maximum tokens per chunk |
| `MIN_COVERAGE_SCORE` | `0.80` | Minimum validation score threshold |
| `CLEANING_MODEL` | `claude-sonnet-4-5-20250929` | Model for transcript cleaning |
| `EXTRACTION_MODEL` | `claude-sonnet-4-5-20250929` | Model for multi-output extraction |
| `ENRICHMENT_MODEL` | `claude-haiku-4-5-20251001` | Model for requirement enrichment |
| `VALIDATION_MODEL` | `claude-haiku-4-5-20251001` | Model for completeness validation |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `TRANSCRIPTS_DIR` | No | Override base directory (default: `.`) |

## Requirements

See [REQUIREMENTS.md](REQUIREMENTS.md) for the full specification as user stories with acceptance criteria.
