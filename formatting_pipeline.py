"""
Cleaning and formatting pipeline for raw meeting transcripts.
Requirement 1: Clean raw transcript once, cache output for downstream extraction.
"""

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
    estimate_token_count,
    load_prompt,
    validate_api_key,
    validate_input_file,
)

load_dotenv()


def clean_transcript(
    raw_filename: str,
    model: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Clean and format a raw meeting transcript.

    Steps:
    1. Load raw transcript from source directory
    2. Check cache -- skip API call if cleaned version exists
    3. Send to Claude for cleaning (remove timestamps, noise, filler words)
    4. Validate conciseness (output tokens < 70% of input)
    5. Save cleaned output to project directory

    Returns:
        dict with keys: base_name, cleaned_path, cleaned_text, token_count,
                        input_tokens, output_tokens, from_cache
    """
    model = model or config.settings.CLEANING_MODEL

    raw_path = config.SOURCE_DIR / raw_filename
    validate_input_file(raw_path)

    base_name = Path(raw_filename).stem
    project_dir = ensure_project_dir(base_name)
    cleaned_path = project_dir / f"{base_name}{config.SUFFIX_CLEANED}"

    # Check cache
    if config.CACHE_CLEANED and cleaned_path.exists():
        if logger:
            logger.info("Using cached cleaned transcript: %s", cleaned_path)
        cleaned_text = cleaned_path.read_text(encoding="utf-8")
        token_count = estimate_token_count(cleaned_text)
        return {
            "base_name": base_name,
            "cleaned_path": str(cleaned_path),
            "cleaned_text": cleaned_text,
            "token_count": token_count,
            "input_tokens": 0,
            "output_tokens": 0,
            "from_cache": True,
        }

    # Load raw transcript
    raw_text = raw_path.read_text(encoding="utf-8")
    input_token_est = estimate_token_count(raw_text)

    if logger:
        logger.info("Raw transcript: %d chars, ~%d tokens", len(raw_text), input_token_est)

    if input_token_est > 15000 and logger:
        logger.warning(
            "Transcript exceeds 15,000 tokens (~%d). Consider chunking for extraction.",
            input_token_est,
        )

    # Load prompt and call Claude
    prompt_text = load_prompt(config.PROMPT_CLEANING_FILENAME)
    api_key = validate_api_key()
    client = Anthropic(api_key=api_key)

    system_msg = create_system_message_with_cache(prompt_text)
    messages = [{"role": "user", "content": raw_text}]

    if logger:
        logger.info("Sending transcript to %s for cleaning...", model)

    message = call_claude_with_retry(
        client=client,
        model=model,
        messages=messages,
        max_tokens=config.MAX_TOKENS_CLEANING,
        temperature=config.TEMP_STRICT,
        logger=logger,
        min_length=100,
        system=system_msg,
        timeout=config.TIMEOUT_CLEANING,
        stream=True,
    )

    cleaned_text = message.content[0].text
    output_token_est = estimate_token_count(cleaned_text)

    # Validate conciseness
    if input_token_est > 0:
        ratio = output_token_est / input_token_est
        if logger:
            logger.info(
                "Conciseness: %d -> %d tokens (%.0f%% of input)",
                input_token_est, output_token_est, ratio * 100,
            )
        if ratio > config.CLEANING_CONCISENESS_RATIO:
            if logger:
                logger.warning(
                    "Cleaned output is %.0f%% of input (threshold: %.0f%%).",
                    ratio * 100, config.CLEANING_CONCISENESS_RATIO * 100,
                )

    # Save cleaned output
    cleaned_path.write_text(cleaned_text, encoding="utf-8")
    if logger:
        logger.info("Saved cleaned transcript: %s", cleaned_path)

    return {
        "base_name": base_name,
        "cleaned_path": str(cleaned_path),
        "cleaned_text": cleaned_text,
        "token_count": output_token_est,
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
        "from_cache": False,
    }
