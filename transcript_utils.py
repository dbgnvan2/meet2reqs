"""
Shared utilities for the meeting transcript processing pipeline.
Provides common validation, API interaction, text processing, and file handling.
"""

import csv
import logging
import os
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from typing import Any, Optional

from anthropic import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    RateLimitError,
)

import config
import model_specs


def setup_logging(script_name: str) -> logging.Logger:
    """Set up logging for a script with file and console handlers."""
    logs_dir = config.LOGS_DIR
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / f"{script_name}_{datetime.now():%Y%m%d_%H%M%S}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    logger = logging.getLogger(script_name)
    logger.info("Logging initialized: %s", log_file)
    return logger


def validate_api_key() -> str:
    """Validate that ANTHROPIC_API_KEY is set and return it."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Set it in your .env file or environment:\n"
            "  export ANTHROPIC_API_KEY='your-api-key-here'"
        )
    return api_key


def validate_input_file(file_path: Path) -> None:
    """Validate that input file exists, is a file, and is not empty."""
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    if file_path.stat().st_size == 0:
        raise ValueError(f"Input file is empty: {file_path}")


def validate_api_response(
    message,
    expected_model: str,
    min_length: int = 50,
    min_words: int = 0,
    logger: Optional[logging.Logger] = None,
) -> str:
    """
    Comprehensive validation of Anthropic API response.
    Returns validated text content or raises on failure.
    """
    if not hasattr(message, "type") or message.type != "message":
        raise ValueError(f"Invalid message type: {getattr(message, 'type', 'missing')}")

    if not hasattr(message, "role") or message.role != "assistant":
        raise ValueError(f"Invalid role: {getattr(message, 'role', 'missing')}")

    stop_reason = getattr(message, "stop_reason", None)
    if stop_reason == "max_tokens":
        raise RuntimeError(
            "Response truncated at token limit. "
            "Increase max_tokens or process in smaller chunks."
        )

    if not hasattr(message, "content") or not message.content:
        raise ValueError("Response has empty content")

    content_block = message.content[0]
    if getattr(content_block, "type", None) != "text":
        raise ValueError(f"Expected text content, got: {getattr(content_block, 'type', 'unknown')}")

    text = getattr(content_block, "text", None)
    if not text or not text.strip():
        raise ValueError("Response contains empty text")

    if len(text) < min_length and logger:
        logger.warning("Response short: %d chars (expected >= %d)", len(text), min_length)

    if min_words > 0 and len(text.split()) < min_words and logger:
        logger.warning("Response short: %d words (expected >= %d)", len(text.split()), min_words)

    if not hasattr(message, "usage"):
        raise ValueError("Response missing usage data")

    if hasattr(message, "model") and message.model != expected_model:
        is_alias = "latest" in expected_model and expected_model.replace("-latest", "") in message.model
        if not is_alias and logger:
            logger.warning("Model mismatch: requested '%s' got '%s'", expected_model, message.model)

    return text


def log_token_usage(script_name: str, model: str, usage_data: object, stop_reason: str):
    """Log token usage and estimated cost to CSV. Never crashes the pipeline."""
    try:
        log_file = config.LOGS_DIR / "token_usage.csv"
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        file_exists = log_file.exists()
        input_tokens = getattr(usage_data, "input_tokens", 0)
        output_tokens = getattr(usage_data, "output_tokens", 0)
        cache_creation = getattr(usage_data, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage_data, "cache_read_input_tokens", 0) or 0

        pricing = model_specs.get_pricing(model)
        total_cost = (
            (input_tokens / 1_000_000) * pricing.get("input", 0)
            + (output_tokens / 1_000_000) * pricing.get("output", 0)
            + (cache_creation / 1_000_000) * pricing.get("cache_write", 0)
            + (cache_read / 1_000_000) * pricing.get("cache_read", 0)
        )

        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Timestamp", "Script", "Model", "Status",
                    "Input Tokens", "Output Tokens",
                    "Cache Created", "Cache Read", "Cost ($)",
                ])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                script_name, model, stop_reason,
                input_tokens, output_tokens,
                cache_creation, cache_read,
                f"{total_cost:.4f}",
            ])
    except Exception as e:
        print(f"Warning: Failed to log token usage: {e}")


def _check_caching_for_large_input(
    messages: list, system: Any, logger: Optional[logging.Logger] = None
):
    """Warn if large inputs are sent without prompt caching."""
    threshold = 10000

    def check_content(content, source_name):
        if isinstance(content, str) and len(content) > threshold:
            msg = f"Large {source_name} ({len(content):,} chars) sent without caching."
            if logger:
                logger.warning(msg)
        elif isinstance(content, list):
            for i, block in enumerate(content):
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if len(text) > threshold and "cache_control" not in block:
                        msg = f"Large {source_name} block {i} ({len(text):,} chars) without caching."
                        if logger:
                            logger.warning(msg)

    if system:
        check_content(system, "system message")
    for i, msg in enumerate(messages):
        check_content(msg.get("content"), f"message {i}")


def call_claude_with_retry(
    client,
    model: str,
    messages: list,
    max_tokens: int,
    temperature: float = config.TEMP_BALANCED,
    max_retries: int = 3,
    logger: Optional[logging.Logger] = None,
    min_length: int = 50,
    min_words: int = 0,
    stream: bool = False,
    **kwargs,
):
    """
    Call Claude API with retry logic and response validation.
    Returns the API response message object.
    """
    current_timeout = kwargs.get("timeout")
    suppress_caching_warnings = kwargs.pop("suppress_caching_warnings", False)

    if not suppress_caching_warnings:
        _check_caching_for_large_input(messages, kwargs.get("system"), logger)

    for attempt in range(max_retries):
        try:
            call_kwargs = kwargs.copy()
            if current_timeout is not None:
                call_kwargs["timeout"] = current_timeout

            is_streaming = stream or call_kwargs.pop("stream", False)

            if is_streaming:
                with client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    **call_kwargs,
                ) as stream_manager:
                    message = stream_manager.get_final_message()
            else:
                message = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    **call_kwargs,
                )

            try:
                validate_api_response(
                    message, expected_model=model,
                    min_length=min_length, min_words=min_words, logger=logger,
                )
                text_content = message.content[0].text
                if len(text_content) < min_length:
                    raise ValueError(f"Response too short: {len(text_content)} chars")
                if min_words > 0 and len(text_content.split()) < min_words:
                    raise ValueError(f"Response too short: {len(text_content.split())} words")
            except (ValueError, RuntimeError):
                if attempt < max_retries - 1:
                    if logger:
                        logger.warning("Retrying due to validation failure (%d/%d)...", attempt + 1, max_retries)
                    continue
                raise

            if message.usage.output_tokens > max_tokens * config.TOKEN_USAGE_WARNING_THRESHOLD:
                if logger:
                    logger.warning("Nearly hit token limit: %d/%d", message.usage.output_tokens, max_tokens)

            if logger:
                cache_read = getattr(message.usage, "cache_read_input_tokens", 0) or 0
                cache_create = getattr(message.usage, "cache_creation_input_tokens", 0) or 0
                cache_msg = ""
                if cache_read > 0:
                    cache_msg = f" (+{cache_read} cached)"
                elif cache_create > 0:
                    cache_msg = f" (created {cache_create} cache)"
                logger.info(
                    "API call OK - Input: %d%s, Output: %d, Stop: %s",
                    message.usage.input_tokens, cache_msg,
                    message.usage.output_tokens, message.stop_reason,
                )

            script_name = getattr(logger, "name", "unknown") if logger else "unknown"
            log_token_usage(script_name, model, message.usage, message.stop_reason)
            return message

        except AuthenticationError as e:
            raise ValueError("ANTHROPIC_API_KEY is invalid or expired.") from e

        except NotFoundError as e:
            raise ValueError(f"Model '{model}' not available (404).") from e

        except BadRequestError as e:
            if "credit balance is too low" in str(e):
                raise ValueError("API credit balance too low.") from e
            raise ValueError(f"API request malformed: {e}") from e

        except APITimeoutError:
            if attempt < max_retries - 1:
                current_timeout = float(current_timeout or 600) * 1.5
                if logger:
                    logger.warning("Timeout, increasing to %.0fs (%d/%d)", current_timeout, attempt + 2, max_retries)
                continue
            raise RuntimeError("API request timed out after retries.")

        except APIConnectionError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                if logger:
                    logger.warning("Connection error, retrying in %ds (%d/%d)", wait_time, attempt + 2, max_retries)
                time.sleep(wait_time)
            else:
                raise RuntimeError("Could not connect to Anthropic API.")

        except RateLimitError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                if logger:
                    logger.warning("Rate limit, waiting %ds (%d/%d)", wait_time, attempt + 2, max_retries)
                time.sleep(wait_time)
            else:
                raise

        except APIError:
            raise


# ============================================================================
# FILE & PATH UTILITIES
# ============================================================================

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and ensure safety."""
    if not filename or not isinstance(filename, str):
        raise ValueError(f"Filename must be a non-empty string, got: {type(filename).__name__}")

    filename = Path(filename).name
    filename = filename.replace("\0", "")

    safe_chars = []
    for char in filename:
        if char in ("/", "\\") or ord(char) < 32:
            continue
        safe_chars.append(char)
    filename = "".join(safe_chars)
    filename = filename.replace("..", "")
    filename = filename.strip().strip(".")

    if not filename:
        raise ValueError("Filename is empty after sanitization")
    if len(filename) > 255:
        raise ValueError(f"Filename too long: {len(filename)} chars (max 255)")
    return filename


def clean_project_name(filename_or_stem: str) -> str:
    """Get the clean base name from a filename, stripping suffixes."""
    stem = Path(filename_or_stem).stem
    while True:
        match = re.search(r"(_validated|_v\d+)$", stem)
        if match:
            stem = stem[: match.start()]
        else:
            break
    return stem


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# ============================================================================
# TOKEN ESTIMATION
# ============================================================================

def estimate_token_count(text: str) -> int:
    """Rough estimate of token count (~4 chars per token)."""
    return len(text) // config.CHARS_PER_TOKEN


def check_token_budget(text: str, max_tokens: int, logger: Optional[logging.Logger] = None) -> bool:
    """Check if text will likely fit within token budget. Returns True if OK."""
    estimated = estimate_token_count(text)
    safe_limit = max_tokens * config.TOKEN_BUDGET_SAFETY_MARGIN
    if estimated > safe_limit:
        if logger:
            logger.warning(
                "Input may exceed token limit: ~%d tokens (safe limit: %d)",
                estimated, int(safe_limit),
            )
        return False
    return True


# ============================================================================
# TEXT PROCESSING
# ============================================================================

def normalize_text(text: str, aggressive: bool = False) -> str:
    """Normalize text for comparison. Aggressive mode removes punctuation and speaker tags."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\[\(]?\b\d+:\d{2}(?:\d{2})?(?:[ap]m)?[\]\)]?", " ", text, flags=re.IGNORECASE)

    if aggressive:
        text = re.sub(r"\*\*[^*]+:\*\*\s*", "", text)
        text = re.sub(r"(Speaker \d+|Unknown Speaker):\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[.,!?;:\u2014\-'\"()]", " ", text)

    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def find_text_in_content(
    needle: str, haystack: str, aggressive_normalization: bool = False
) -> tuple[Optional[int], Optional[int], float]:
    """Find needle in haystack using fuzzy matching. Returns (start, end, ratio)."""
    needle_n = normalize_text(needle, aggressive=aggressive_normalization)
    haystack_n = normalize_text(haystack, aggressive=aggressive_normalization)

    if needle_n in haystack_n:
        search_start = needle[: min(config.FUZZY_MATCH_PREFIX_LEN, len(needle))].strip()
        pos = haystack.lower().find(search_start.lower())
        if pos >= 0:
            return (pos, pos + len(needle), 1.0)

    needle_words = needle_n.split()
    haystack_words = haystack_n.split()
    needle_len = len(needle_words)

    best_ratio = 0.0
    best_pos = None

    for i in range(len(haystack_words) - needle_len + 1):
        window = " ".join(haystack_words[i : i + needle_len])
        ratio = SequenceMatcher(None, needle_n, window).ratio()
        if ratio > best_ratio and ratio >= config.FUZZY_MATCH_THRESHOLD:
            best_ratio = ratio
            best_pos = i
            if ratio >= config.FUZZY_MATCH_EARLY_STOP:
                break

    if best_pos is not None:
        words_before = " ".join(haystack_words[:best_pos])
        approx_start = len(words_before)
        approx_end = approx_start + len(" ".join(haystack_words[best_pos : best_pos + needle_len]))
        return (approx_start, approx_end, best_ratio)

    return (None, None, 0.0)


# ============================================================================
# MARKDOWN UTILITIES
# ============================================================================

def extract_section(content: str, section_name: str) -> str:
    """Extract a markdown section by name, handling nested subsections."""
    escaped_name = re.escape(section_name).replace(r"\ ", r"\s+")
    start_pattern = re.compile(
        rf"^(#*)\s*(?:[\*\_]+)?(?:\d+\.?\s*)?{escaped_name}\b.*?$",
        re.MULTILINE | re.IGNORECASE,
    )

    match = start_pattern.search(content)
    if not match:
        return ""

    start_level = len(match.group(1)) if match.group(1) else 2
    start_pos = match.end()

    header_pattern = re.compile(r"^(#+)\s", re.MULTILINE)
    for next_header in header_pattern.finditer(content, start_pos):
        if len(next_header.group(1)) <= start_level:
            return content[start_pos : next_header.start()].strip()

    return content[start_pos:].strip()


def strip_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    match = re.match(r"^\s*---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if match:
        return content[match.end() :]
    return content


def markdown_to_html(text: str) -> str:
    """Convert basic markdown to HTML."""
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    paragraphs = text.split("\n\n")
    paragraphs = [
        f"<p>{p.strip()}</p>" if not p.strip().startswith("<") else p.strip()
        for p in paragraphs
        if p.strip()
    ]
    return "\n".join(paragraphs)


def create_system_message_with_cache(text: str) -> list:
    """Create a system message with Anthropic prompt caching enabled."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def delete_logs(logger=None) -> bool:
    """Permanently delete log files and token usage CSV."""
    if logger is None:
        logger = setup_logging("delete_logs")
    logs_dir = config.LOGS_DIR
    if not logs_dir.exists():
        return True
    files = list(logs_dir.glob("*.log")) + list(logs_dir.glob("*.csv"))
    for f in files:
        f.unlink()
        logger.info("Deleted: %s", f.name)
    return True


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = config.PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def ensure_project_dir(base_name: str) -> Path:
    """Ensure the project output directory exists and return its path."""
    project_dir = config.PROJECTS_DIR / base_name
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir
