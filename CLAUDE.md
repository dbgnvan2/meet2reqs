# CLAUDE.md

## Project Overview

**trans-summary** is a Python-based automated transcript processing pipeline. It takes raw audio/video transcripts through formatting, structured extraction (topics, themes, key terms, emphasis, Bowen references), summarization, validation, and multi-format output generation (HTML, PDF). It offers both a Tkinter GUI and a CLI interface.

## Tech Stack

- **Language**: Python 3.11+
- **AI**: Anthropic Claude API (`anthropic==0.75.0`)
- **HTML/PDF**: Jinja2 templates, WeasyPrint, BeautifulSoup4
- **Testing**: pytest
- **Linting/Formatting**: ruff (Black-compatible, line-length 88)
- **CI**: GitHub Actions (Python 3.8-3.11 matrix)

## Repository Structure

```
meet2reqs/
├── pipeline.py                  # Facade orchestrating all pipeline modules
├── config.py                    # Singleton ProjectSettings (paths, models, validation)
├── model_specs.py               # Model pricing and specifications
├── transcript_utils.py          # Shared utilities and API interaction helpers
│
├── formatting_pipeline.py       # Raw transcript -> formatted Markdown
├── extraction_pipeline.py       # Extract topics, themes, emphasis, Bowen refs
├── abstract_pipeline.py         # Abstract generation
├── summary_pipeline.py          # Summary generation
├── validation_pipeline.py       # Header, abstract, coverage validation
├── summary_validation.py        # Deep summary validation
├── abstract_validation.py       # Coverage & structural validation
├── emphasis_detector.py         # Fuzzy-match emphasis detection
├── html_generator.py            # Jinja2-based HTML/PDF output
├── cleanup_pipeline.py          # Cleanup utilities
├── packaging_pipeline.py        # Package transcript artifacts
│
├── transcript_process.py        # Interactive CLI wizard (main entry point)
├── transcript_processor_gui.py  # Tkinter GUI application
├── transcript_format.py         # CLI: format a transcript
├── transcript_add_yaml.py       # CLI: add YAML metadata
├── transcript_summarize.py      # CLI: generate summary
├── transcript_to_webpage.py     # CLI: generate HTML webpage
├── transcript_to_pdf.py         # CLI: generate PDF
├── transcript_validate_*.py     # CLI: various validation scripts
│
├── prompts/                     # Markdown prompt templates for Claude API
├── templates/                   # Jinja2 HTML templates + CSS
├── tests/                       # pytest test suite (17 test files)
├── source/                      # Input transcripts directory
├── projects/                    # Output artifacts per project
├── logs/                        # Timestamped process logs
│
├── pyproject.toml               # Build config, ruff settings
├── requirements.txt             # Pinned dependencies
├── .env.example                 # Environment variable template
└── .github/workflows/ci.yml     # CI pipeline
```

## Key Architecture Patterns

- **Pipeline Pattern**: `pipeline.py` is the facade that re-exports functions from specialized modules (`formatting_pipeline`, `extraction_pipeline`, `summary_pipeline`, `validation_pipeline`, `html_generator`).
- **Singleton Config**: `config.py` uses `ProjectSettings` singleton for all paths and model settings. Access via `config.settings` or legacy module-level proxies.
- **Model-Agnostic Design**: API interactions are abstracted for potential multi-provider support.
- **Prompt Caching**: Uses Anthropic ephemeral cache for cost reduction (62-85% savings).
- **Multi-layer Validation**: 7 validation levels (API response, initial transcript, format, headers, coverage, fidelity, completeness).

## Development Commands

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run tests
```bash
pytest                              # All tests
pytest tests/                       # Tests in tests/ directory only
pytest tests/test_specific.py       # Single test file
pytest --cov=. --cov-report=html    # With coverage report
```

### Lint and format
```bash
ruff check .          # Lint all files
ruff check . --fix    # Auto-fix lint issues
ruff format .         # Auto-format (Black-compatible)
```

### Validate configuration
```bash
python -c "import config; config.validate_or_exit()"
```

### Run the application
```bash
python transcript_processor_gui.py          # GUI mode
python transcript_process.py                # Interactive CLI
python transcript_format.py "file.txt"      # Format a single transcript
```

## Environment Setup

1. Copy `.env.example` to `.env`
2. Set `ANTHROPIC_API_KEY` (required)
3. Optionally set `TRANSCRIPTS_DIR` to override the default base path

## Code Conventions

- **Style**: PEP 8 via ruff. Line length 88. Double quotes. 4-space indent.
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `_prefix` for private functions, `test_` prefix for tests.
- **Tests**: Use `unittest.TestCase` with pytest runner. Mock Claude API calls with `unittest.mock.patch` and `MagicMock`. Use `tempfile` for file I/O tests.
- **Error handling**: Categorized exceptions with context. API responses go through 7-level validation. Retry logic with exponential backoff for API calls.
- **Security**: Path traversal protection (sanitize `../`, null bytes, control chars), XSS prevention via Jinja2 auto-escaping, API keys via environment variables only.

## Data Flow

```
Raw Transcript (source/)
  -> format_transcript()          -> Formatted Markdown
  -> add_yaml()                   -> YAML metadata header added
  -> summarize_transcript()       -> Topics, Themes, Summary, Abstract extracted
  -> validate_headers/coverage()  -> Quality checks
  -> generate_webpage/pdf()       -> HTML/PDF output (projects/)
```

## Models Used

| Purpose       | Model                           | Notes                    |
|---------------|---------------------------------|--------------------------|
| Default       | claude-3-7-sonnet-20250219      | Supports caching         |
| Formatting    | claude-3-7-sonnet-20250219      | Extended output          |
| Auxiliary     | claude-3-5-haiku-20241022       | Cost-effective           |
| Validation    | claude-3-5-haiku-20241022       | Cheaper for QA           |

## Pre-commit Checklist

1. All tests pass: `pytest`
2. Configuration validates: `python -c "import config; config.validate_or_exit()"`
3. Code formatted: `ruff format .`
4. Linting passes: `ruff check .`
5. New features include tests
6. No hardcoded API keys or secrets

## Important Notes for AI Assistants

- The project root is the Python path -- modules import each other directly (e.g., `from config import settings`, `from pipeline import format_transcript`).
- There are test files both in `tests/` and at the project root. The canonical test suite lives in `tests/`. Root-level `test_*.py` files are ad-hoc/debug tests.
- `pipeline.py` is the central import hub. When adding new pipeline functions, export them through this facade.
- Prompt templates in `prompts/` are Markdown files fed to the Claude API. Changes to prompts affect AI output quality.
- `html_generator.py` uses Jinja2 templates from `templates/`. Always use auto-escaping for user content.
- The `summary_validation.py` file is very large (~30K lines). Prefer targeted reads when working with it.
- CI uses `|| true` on test/install steps, so failures don't block the pipeline. Treat test failures as real issues regardless.
