"""
Chunking module for splitting long transcripts into processable segments.
Requirement 2: Optional chunking at natural boundaries with configurable overlap.
"""

import logging
import re
from typing import Optional

import tiktoken

import config
from transcript_utils import estimate_token_count


def _get_encoder():
    """Get tiktoken encoder, falling back to cl100k_base."""
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken if available, otherwise estimate."""
    encoder = _get_encoder()
    if encoder:
        return len(encoder.encode(text))
    return estimate_token_count(text)


def needs_chunking(text: str) -> bool:
    """Check if text exceeds the chunking threshold."""
    return count_tokens(text) > config.CHUNK_THRESHOLD


def _find_split_points(text: str) -> list[int]:
    """
    Find natural split points in text (paragraph breaks, speaker turns).
    Returns list of character positions suitable for splitting.
    """
    split_points = []

    # Priority 1: Double newlines (paragraph breaks)
    for match in re.finditer(r"\n\n+", text):
        split_points.append(match.end())

    # Priority 2: Speaker labels (e.g., "**Name:**" at line start)
    for match in re.finditer(r"\n\*\*[^*]+:\*\*", text):
        split_points.append(match.start() + 1)  # After the newline

    # Priority 3: Single newlines as fallback
    if not split_points:
        for match in re.finditer(r"\n", text):
            split_points.append(match.end())

    return sorted(set(split_points))


def chunk_text(
    text: str,
    max_tokens: Optional[int] = None,
    overlap_tokens: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
) -> list[dict]:
    """
    Split text into chunks at natural boundaries with overlap.

    Args:
        text: The cleaned transcript text to chunk
        max_tokens: Maximum tokens per chunk (default: config.CHUNK_MAX_TOKENS)
        overlap_tokens: Overlap between chunks (default: config.CHUNK_OVERLAP_TOKENS)
        logger: Optional logger

    Returns:
        List of dicts: [{"index": 0, "text": "...", "tokens": 1234}, ...]
    """
    max_tokens = max_tokens or config.CHUNK_MAX_TOKENS
    overlap_tokens = overlap_tokens or config.CHUNK_OVERLAP_TOKENS

    total_tokens = count_tokens(text)
    if total_tokens <= max_tokens:
        if logger:
            logger.info("Text fits in single chunk (%d tokens)", total_tokens)
        return [{"index": 0, "text": text, "tokens": total_tokens}]

    split_points = _find_split_points(text)
    if not split_points:
        # No natural split points; fall back to character-based splitting
        split_points = list(range(0, len(text), len(text) // (total_tokens // max_tokens + 1)))

    chunks = []
    chunk_start = 0
    chunk_index = 0

    while chunk_start < len(text):
        # Find the furthest split point within the token budget
        best_end = None
        for sp in split_points:
            if sp <= chunk_start:
                continue
            segment = text[chunk_start:sp]
            if count_tokens(segment) > max_tokens:
                break
            best_end = sp

        if best_end is None:
            # No good split point found; take up to max characters
            chars_est = max_tokens * config.CHARS_PER_TOKEN
            best_end = min(chunk_start + chars_est, len(text))

        chunk_text_segment = text[chunk_start:best_end].strip()
        if chunk_text_segment:
            chunks.append({
                "index": chunk_index,
                "text": chunk_text_segment,
                "tokens": count_tokens(chunk_text_segment),
            })
            chunk_index += 1

        # Move start back by overlap amount
        overlap_chars = overlap_tokens * config.CHARS_PER_TOKEN
        chunk_start = max(best_end - overlap_chars, best_end)

        # Avoid infinite loop
        if chunk_start >= len(text) or best_end >= len(text):
            break

    if logger:
        logger.info(
            "Split text into %d chunks (total: %d tokens, max/chunk: %d)",
            len(chunks), total_tokens, max_tokens,
        )

    return chunks


def aggregate_extractions(chunk_results: list[dict], logger: Optional[logging.Logger] = None) -> dict:
    """
    Aggregate extraction results from multiple chunks.
    Merges lists and deduplicates by comparing text content.

    Args:
        chunk_results: List of extraction result dicts (one per chunk)
        logger: Optional logger

    Returns:
        Single merged extraction dict with all categories combined
    """
    if not chunk_results:
        return {}

    if len(chunk_results) == 1:
        return chunk_results[0]

    merged = {}
    for category in config.EXTRACTION_CATEGORIES:
        all_items = []
        seen_texts = set()

        for result in chunk_results:
            items = result.get(category, [])
            for item in items:
                # Create a dedup key from the main text content
                if isinstance(item, dict):
                    dedup_key = _dedup_key(item)
                else:
                    dedup_key = str(item).lower().strip()

                if dedup_key not in seen_texts:
                    seen_texts.add(dedup_key)
                    all_items.append(item)

        merged[category] = all_items

    if logger:
        for cat in config.EXTRACTION_CATEGORIES:
            logger.info("Aggregated %s: %d items", cat, len(merged.get(cat, [])))

    return merged


def _dedup_key(item: dict) -> str:
    """Create a deduplication key from a structured item."""
    # Use the most descriptive field available
    for field in ["user_story", "description", "task", "name", "phrase"]:
        if field in item:
            return item[field].lower().strip()[:100]
    return str(sorted(item.items()))[:100]
