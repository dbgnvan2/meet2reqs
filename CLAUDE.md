# CLAUDE.md

## Project Overview

**meet2reqs** is a Python pipeline that processes meeting transcripts into structured, actionable outputs: requirements (user stories with acceptance criteria), decisions, action items, technology stack, and emphasized items. It uses Anthropic's Claude API with token-efficient caching, chunking, and multi-task prompting. Offers both a Tkinter GUI and interactive CLI.

## Tech Stack

- **Language**: Python 3.11+
- **AI**: Anthropic Claude API (`anthropic>=0.75.0`)
- **Token Counting**: tiktoken
- **HTML/PDF**: Jinja2 templates, WeasyPrint
- **Testing**: pytest (127 tests)
- **Linting/Formatting**: ruff (Black-compatible, line-length 88)

## Repository Structure

```
meet2reqs/
├── config.py                    # Singleton settings: models, paths, thresholds, validation
├── model_specs.py               # Model pricing and specifications
├── transcript_utils.py          # Shared utilities: API calls, text processing, file I/O
│
├── formatting_pipeline.py       # Step 1: Clean raw transcript, cache output
├── chunking.py                  # Step 2: Split long transcripts at natural boundaries
├── extraction_pipeline.py       # Step 3: Multi-output extraction (5 categories in 1 call)
├── enrichment_pipeline.py       # Step 4: Enrich user stories with acceptance criteria
├── validation_pipeline.py       # Step 5: Multi-level validation (structure, fidelity, INVEST)
├── html_generator.py            # Step 6: Generate Markdown, HTML, PDF reports
├── pipeline.py                  # Facade: re-exports all pipeline functions
│
├── transcript_process.py        # Interactive CLI
├── transcript_processor_gui.py  # Tkinter GUI
│
├── prompts/                     # LLM prompt templates
│   ├── cleaning.md              # Transcript cleaning prompt
│   ├── extraction.md            # Multi-output extraction prompt (JSON schema)
│   ├── enrichment.md            # User story enrichment prompt (GWT format)
│   └── validation.md            # Completeness validation prompt
│
├── templates/                   # Jinja2 HTML templates + CSS
│   ├── report.html              # Web report template
│   ├── pdf.html                 # PDF report template
│   └── styles/pdf.css           # Print-optimized CSS
│
├── tests/                       # pytest test suite (127 tests)
├── source/                      # Input transcripts
├── projects/                    # Output artifacts per transcript
├── logs/                        # Timestamped process logs + token_usage.csv
│
├── REQUIREMENTS.md              # Full specification as user stories
├── pyproject.toml               # Build config, ruff settings
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variable template
```

## Pipeline Data Flow

```
Raw Transcript (source/)
  -> clean_transcript()        -> cleaned.md (file-cached)
  -> needs_chunking()          -> chunk if > 10K tokens
  -> extract_all()             -> 5 JSON files (requirements, decisions, actions, tech, emphasis)
  -> enrich_requirements()     -> enriched_requirements.json (GWT acceptance criteria)
  -> validate_extraction()     -> validation_report.json (structure + fidelity + INVEST + completeness)
  -> generate_*_report()       -> report.md, report.html, report.pdf
```

## Development Commands

```bash
pip install -r requirements.txt                  # Install dependencies
pytest tests/                                     # Run all 127 tests
pytest tests/test_specific.py -v                  # Single test file
ruff check .                                      # Lint
ruff format .                                     # Format
python -c "import config; config.validate_or_exit()"  # Validate config
python transcript_process.py                      # Run CLI
python transcript_processor_gui.py                # Run GUI
```

## Key Architecture Patterns

- **Pipeline Pattern**: `pipeline.py` is the facade re-exporting functions from specialized modules
- **Singleton Config**: `config.py` uses `ProjectSettings` with backward-compatible module-level proxies
- **File-Based Caching**: Cleaned transcripts cached to avoid redundant API calls (Req 1)
- **Smart Chunking**: Splits at paragraph/speaker boundaries with overlap (Req 2)
- **Multi-Task Extraction**: Single API call extracts all 5 categories into structured JSON (Req 3)
- **Agile Enrichment**: Automatic Given-When-Then acceptance criteria from best practices (Req 4)
- **Multi-Level Validation**: Structure, fidelity, INVEST compliance, GWT format, LLM completeness (Req 5)
- **Triple-Format Output**: Markdown, HTML, PDF from Jinja2 templates (Req 6)

## Extraction Categories

| Category | JSON Key | Required Fields | Description |
|----------|----------|----------------|-------------|
| Requirements | `requirements` | `user_story` | INVEST-compliant user stories |
| Decisions | `decisions` | `decision`, `rationale` | Outcomes with reasoning and status |
| Action Items | `action_items` | `task` | Tasks with assignee and deadline |
| Tech Stack | `technology_stack` | `name` | Tools/frameworks with category and context |
| Emphasized Items | `emphasized_items` | `phrase` | Key statements with speaker and emphasis type |

## Code Conventions

- **Style**: PEP 8 via ruff. Line length 88. Double quotes. 4-space indent.
- **Naming**: `snake_case` functions/variables, `PascalCase` classes, `_prefix` private, `test_` prefix tests.
- **Tests**: `unittest.TestCase` with pytest runner. Mock API calls with `unittest.mock`. Use `tempfile` for file I/O.
- **Error handling**: Categorized exceptions with context. API retry with exponential backoff.
- **Security**: Path traversal protection, XSS prevention via Jinja2 auto-escaping, API keys via env vars only.

## Models Used

| Role | Default Model | Purpose |
|------|--------------|---------|
| Cleaning | claude-sonnet-4-5-20250929 | Remove noise, format as Markdown |
| Extraction | claude-sonnet-4-5-20250929 | Multi-output category extraction |
| Enrichment | claude-haiku-4-5-20251001 | Add acceptance criteria (cost-effective) |
| Validation | claude-haiku-4-5-20251001 | Completeness checking (cost-effective) |

## Important Notes for AI Assistants

- The project root is the Python path -- modules import directly (e.g., `from config import settings`)
- `pipeline.py` is the single import hub. New pipeline functions should be exported there.
- Prompts in `prompts/` are Markdown fed to Claude API. Changes affect extraction quality.
- Extraction response must be valid JSON matching the schema in `prompts/extraction.md`.
- `enrichment_pipeline.py` flags ambiguous stories with `"confidence": "low"` for manual review.
- Validation has 5 levels: structure, fidelity (fuzzy match to transcript), INVEST compliance, GWT format, LLM completeness.
- `chunking.py` uses tiktoken for accurate token counts; falls back to char-based estimation.
- All file suffixes defined in `config.py` (SUFFIX_*). Consistency matters for cache lookups.
