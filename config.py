"""
Configuration for the meeting transcript processing pipeline.
Processes meeting transcripts into structured outputs: requirements (user stories),
decisions, action items, technology stack, and emphasized items.

Uses a Singleton pattern for settings. Direct access to variables
(e.g. config.SOURCE_DIR) is proxied to the singleton instance.
"""

import os
import sys
from pathlib import Path
from typing import Union, List

import model_specs


class ProjectSettings:
    """Singleton class to manage project settings and paths."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProjectSettings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.TRANSCRIPTS_BASE = Path(os.getenv("TRANSCRIPTS_DIR", "."))
        self._update_derived_paths()

        # Model assignments by role
        self.CLEANING_MODEL = "claude-sonnet-4-5-20250929"
        self.EXTRACTION_MODEL = "claude-sonnet-4-5-20250929"
        self.ENRICHMENT_MODEL = "claude-haiku-4-5-20251001"
        self.VALIDATION_MODEL = "claude-haiku-4-5-20251001"

        self._initialized = True

    def _update_derived_paths(self):
        """Update paths derived from TRANSCRIPTS_BASE."""
        self.SOURCE_DIR = self.TRANSCRIPTS_BASE / "source"
        self.PROCESSED_DIR = self.TRANSCRIPTS_BASE / "processed"
        self.PROJECTS_DIR = self.TRANSCRIPTS_BASE / "projects"
        self.PROMPTS_DIR = Path(__file__).parent / "prompts"
        self.TEMPLATES_DIR = Path(__file__).parent / "templates"
        self.LOGS_DIR = Path(__file__).parent / "logs"

    def set_transcripts_base(self, path: Union[str, Path]):
        """Update the base directory for transcripts and all related paths."""
        self.TRANSCRIPTS_BASE = Path(path)
        self._update_derived_paths()

    def get_all_model_names(self) -> list[str]:
        """Returns a list of all model names from model_specs.PRICING."""
        return sorted(model_specs.PRICING.keys())

    def set_model(self, role: str, model_name: str):
        """Set a model for a given role (cleaning, extraction, enrichment, validation)."""
        attr = f"{role.upper()}_MODEL"
        if not hasattr(self, attr):
            raise ValueError(f"Unknown model role: '{role}'")
        if model_name not in model_specs.PRICING:
            raise ValueError(f"Model '{model_name}' not found in model_specs.PRICING.")
        setattr(self, attr, model_name)


# Initialize the singleton
settings = ProjectSettings()


# Backward compatibility proxies
def __getattr__(name):
    if hasattr(settings, name):
        return getattr(settings, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


TRANSCRIPTS_BASE = settings.TRANSCRIPTS_BASE
SOURCE_DIR = settings.SOURCE_DIR
PROCESSED_DIR = settings.PROCESSED_DIR
PROJECTS_DIR = settings.PROJECTS_DIR
PROMPTS_DIR = settings.PROMPTS_DIR
TEMPLATES_DIR = settings.TEMPLATES_DIR
LOGS_DIR = settings.LOGS_DIR

CLEANING_MODEL = settings.CLEANING_MODEL
EXTRACTION_MODEL = settings.EXTRACTION_MODEL
ENRICHMENT_MODEL = settings.ENRICHMENT_MODEL
VALIDATION_MODEL = settings.VALIDATION_MODEL


def set_transcripts_base(path: Union[str, Path]):
    """Global function to update the singleton settings."""
    settings.set_transcripts_base(path)
    global TRANSCRIPTS_BASE, SOURCE_DIR, PROCESSED_DIR, PROJECTS_DIR
    TRANSCRIPTS_BASE = settings.TRANSCRIPTS_BASE
    SOURCE_DIR = settings.SOURCE_DIR
    PROCESSED_DIR = settings.PROCESSED_DIR
    PROJECTS_DIR = settings.PROJECTS_DIR


# ============================================================================
# CONSTANTS
# ============================================================================

# File Suffixes
SUFFIX_CLEANED = " - cleaned.md"
SUFFIX_REQUIREMENTS = " - requirements.json"
SUFFIX_DECISIONS = " - decisions.json"
SUFFIX_ACTION_ITEMS = " - action_items.json"
SUFFIX_TECH_STACK = " - tech_stack.json"
SUFFIX_EMPHASIZED = " - emphasized_items.json"
SUFFIX_ENRICHED = " - enriched_requirements.json"
SUFFIX_VALIDATION_REPORT = " - validation_report.json"
SUFFIX_REPORT_MD = " - report.md"
SUFFIX_REPORT_HTML = " - report.html"
SUFFIX_REPORT_PDF = " - report.pdf"

# Cleaning & Caching
CACHE_CLEANED = True
CLEANING_CONCISENESS_RATIO = 0.70  # cleaned output tokens < 70% of input

# Chunking
CHUNK_THRESHOLD = 10000       # tokens: only chunk if cleaned text exceeds this
CHUNK_MAX_TOKENS = 4000       # max tokens per chunk
CHUNK_OVERLAP_TOKENS = 200    # overlap between chunks

# Token Limits
MAX_TOKENS_CLEANING = 32000
MAX_TOKENS_EXTRACTION = 16384
MAX_TOKENS_ENRICHMENT = 8192
MAX_TOKENS_VALIDATION = 4096

# Temperature Settings
TEMP_STRICT = 0.0
TEMP_ANALYSIS = 0.2
TEMP_BALANCED = 0.3

# Timeouts (seconds)
TIMEOUT_CLEANING = 600    # 10 minutes
TIMEOUT_EXTRACTION = 600  # 10 minutes
TIMEOUT_ENRICHMENT = 300  # 5 minutes
TIMEOUT_VALIDATION = 300  # 5 minutes
TIMEOUT_DEFAULT = 300     # 5 minutes

# Prompt Filenames
PROMPT_CLEANING_FILENAME = "cleaning.md"
PROMPT_EXTRACTION_FILENAME = "extraction.md"
PROMPT_ENRICHMENT_FILENAME = "enrichment.md"
PROMPT_VALIDATION_FILENAME = "validation.md"

# Validation Settings
MIN_COVERAGE_SCORE = 0.80
ENRICHMENT_CONFIDENCE_THRESHOLD = 0.70

# Token Estimation
CHARS_PER_TOKEN = 4
TOKEN_BUDGET_SAFETY_MARGIN = 0.8
TOKEN_USAGE_WARNING_THRESHOLD = 0.9

# Fuzzy Matching
FUZZY_MATCH_THRESHOLD = 0.85
FUZZY_MATCH_EARLY_STOP = 0.98
FUZZY_MATCH_PREFIX_LEN = 20

# Extraction JSON Schema Keys (for validation)
EXTRACTION_CATEGORIES = [
    "requirements",
    "decisions",
    "action_items",
    "technology_stack",
    "emphasized_items",
]


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

class ValidationResult:
    """Stores validation results with errors and warnings."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def format_report(self) -> str:
        lines = []
        if self.errors:
            lines.append("=" * 70)
            lines.append("CONFIGURATION ERRORS")
            lines.append("=" * 70)
            for i, error in enumerate(self.errors, 1):
                lines.append(f"{i}. {error}")
            lines.append("")
        if self.warnings:
            lines.append("=" * 70)
            lines.append("CONFIGURATION WARNINGS")
            lines.append("=" * 70)
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"{i}. {warning}")
            lines.append("")
        if not self.errors and not self.warnings:
            lines.append("Configuration validation passed - no issues found.")
        return "\n".join(lines)


def validate_configuration(verbose: bool = True, auto_fix: bool = False) -> ValidationResult:
    """Validate all configuration settings for correctness and consistency."""
    result = ValidationResult()

    # 1. Validate directory paths
    if not settings.TRANSCRIPTS_BASE.exists():
        if auto_fix:
            try:
                settings.TRANSCRIPTS_BASE.mkdir(parents=True, exist_ok=True)
                result.add_warning(f"Created TRANSCRIPTS_BASE: {settings.TRANSCRIPTS_BASE}")
            except Exception as e:
                result.add_error(f"TRANSCRIPTS_BASE cannot be created: {settings.TRANSCRIPTS_BASE} ({e})")
        else:
            result.add_error(
                f"TRANSCRIPTS_BASE does not exist: {settings.TRANSCRIPTS_BASE}\n"
                f"  Fix: export TRANSCRIPTS_DIR=/path/to/transcripts"
            )
    elif not settings.TRANSCRIPTS_BASE.is_dir():
        result.add_error(f"TRANSCRIPTS_BASE is not a directory: {settings.TRANSCRIPTS_BASE}")

    for name, path in [("SOURCE_DIR", settings.SOURCE_DIR),
                       ("PROCESSED_DIR", settings.PROCESSED_DIR),
                       ("PROJECTS_DIR", settings.PROJECTS_DIR)]:
        if not path.exists():
            if auto_fix:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    result.add_warning(f"Created {name}: {path}")
                except Exception as e:
                    result.add_error(f"{name} cannot be created: {path} ({e})")
            else:
                result.add_warning(f"{name} does not exist: {path} (will be created when needed)")

    if not settings.PROMPTS_DIR.exists():
        result.add_error(f"PROMPTS_DIR does not exist: {settings.PROMPTS_DIR}")

    if not settings.LOGS_DIR.exists():
        if auto_fix:
            try:
                settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
                result.add_warning(f"Created LOGS_DIR: {settings.LOGS_DIR}")
            except Exception as e:
                result.add_error(f"LOGS_DIR cannot be created: {settings.LOGS_DIR} ({e})")

    # 2. Validate model names
    for role in ["CLEANING_MODEL", "EXTRACTION_MODEL", "ENRICHMENT_MODEL", "VALIDATION_MODEL"]:
        model_name = getattr(settings, role)
        if model_name not in model_specs.PRICING:
            result.add_error(f"{role} specifies unknown model: '{model_name}'")

    # 3. Validate numeric ranges
    token_limits = {
        "MAX_TOKENS_CLEANING": MAX_TOKENS_CLEANING,
        "MAX_TOKENS_EXTRACTION": MAX_TOKENS_EXTRACTION,
        "MAX_TOKENS_ENRICHMENT": MAX_TOKENS_ENRICHMENT,
        "MAX_TOKENS_VALIDATION": MAX_TOKENS_VALIDATION,
    }
    for name, value in token_limits.items():
        if not isinstance(value, int) or value <= 0:
            result.add_error(f"{name} must be a positive integer, got: {value}")

    temperatures = {
        "TEMP_STRICT": TEMP_STRICT,
        "TEMP_ANALYSIS": TEMP_ANALYSIS,
        "TEMP_BALANCED": TEMP_BALANCED,
    }
    for name, value in temperatures.items():
        if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
            result.add_error(f"{name} must be between 0.0 and 1.0, got: {value}")

    timeouts = {
        "TIMEOUT_CLEANING": TIMEOUT_CLEANING,
        "TIMEOUT_EXTRACTION": TIMEOUT_EXTRACTION,
        "TIMEOUT_ENRICHMENT": TIMEOUT_ENRICHMENT,
        "TIMEOUT_VALIDATION": TIMEOUT_VALIDATION,
        "TIMEOUT_DEFAULT": TIMEOUT_DEFAULT,
    }
    for name, value in timeouts.items():
        if not isinstance(value, (int, float)) or value <= 0:
            result.add_error(f"{name} must be positive, got: {value}")

    # 4. Validate chunking consistency
    if CHUNK_OVERLAP_TOKENS >= CHUNK_MAX_TOKENS:
        result.add_error(
            f"CHUNK_OVERLAP_TOKENS ({CHUNK_OVERLAP_TOKENS}) must be < "
            f"CHUNK_MAX_TOKENS ({CHUNK_MAX_TOKENS})"
        )

    if CHUNK_THRESHOLD < CHUNK_MAX_TOKENS:
        result.add_warning(
            f"CHUNK_THRESHOLD ({CHUNK_THRESHOLD}) < CHUNK_MAX_TOKENS ({CHUNK_MAX_TOKENS}). "
            f"Chunking will always produce a single chunk."
        )

    # 5. Validate prompt files exist
    if settings.PROMPTS_DIR.exists():
        prompt_files = {
            "PROMPT_CLEANING_FILENAME": PROMPT_CLEANING_FILENAME,
            "PROMPT_EXTRACTION_FILENAME": PROMPT_EXTRACTION_FILENAME,
            "PROMPT_ENRICHMENT_FILENAME": PROMPT_ENRICHMENT_FILENAME,
            "PROMPT_VALIDATION_FILENAME": PROMPT_VALIDATION_FILENAME,
        }
        missing = []
        for name, filename in prompt_files.items():
            if not (settings.PROMPTS_DIR / filename).exists():
                missing.append(f"  - {name}: {filename}")
        if missing:
            result.add_warning(
                f"Missing prompt file(s) in {settings.PROMPTS_DIR}:\n" + "\n".join(missing)
            )

    # 6. Validate percentages/ratios
    for name, value in [("MIN_COVERAGE_SCORE", MIN_COVERAGE_SCORE),
                        ("ENRICHMENT_CONFIDENCE_THRESHOLD", ENRICHMENT_CONFIDENCE_THRESHOLD),
                        ("CLEANING_CONCISENESS_RATIO", CLEANING_CONCISENESS_RATIO),
                        ("TOKEN_BUDGET_SAFETY_MARGIN", TOKEN_BUDGET_SAFETY_MARGIN),
                        ("FUZZY_MATCH_THRESHOLD", FUZZY_MATCH_THRESHOLD)]:
        if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
            result.add_error(f"{name} must be between 0.0 and 1.0, got: {value}")

    if verbose:
        print(result.format_report())
    return result


def validate_or_exit(verbose: bool = True, auto_fix: bool = False):
    """Validate configuration and exit if validation fails."""
    result = validate_configuration(verbose=verbose, auto_fix=auto_fix)
    if not result.is_valid():
        print("\n" + "=" * 70)
        print("CRITICAL: Configuration validation failed")
        print("=" * 70)
        print("Please fix the errors above and try again.")
        sys.exit(1)
    elif result.warnings and verbose:
        print("\nConfiguration has warnings but is usable.\n")
