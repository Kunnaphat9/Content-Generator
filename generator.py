"""Content generation logic: selects chunk × dimension, calls Claude API."""

import logging
import os
import random

import anthropic

from knowledge import extract_chunk_ids, fetch_chunk_map, fetch_knowledge_file, get_chunk_metadata
from prompts import (
    DIMENSIONS,
    build_outlines_system_prompt,
    build_outlines_user_message,
    build_full_article_system_prompt,
    build_full_article_user_message,
)

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_TOKENS_OUTLINES = 2000
MAX_TOKENS_ARTICLE = 2000


async def _build_chunk_data(chunk_id: str, chunk_map: dict) -> dict:
    """Fetch knowledge file and normalize into chunk_data dict."""
    raw_knowledge = await fetch_knowledge_file(chunk_id)
    chunk_meta = get_chunk_metadata(chunk_map, chunk_id)

    raw_content = raw_knowledge.get("content", "")
    if isinstance(raw_content, list):
        parts = []
        for section in raw_content:
            if section.get("title"):
                parts.append(section["title"])
            for para in section.get("paragraphs", []):
                if para.get("text"):
                    parts.append(para["text"])
            for sub in section.get("subsections", []):
                if sub.get("title"):
                    parts.append(sub["title"])
                for para in sub.get("paragraphs", []):
                    if para.get("text"):
                        parts.append(para["text"])
        raw_content = "\n\n".join(parts)

    return {
        "title": chunk_meta.get("label") or raw_knowledge.get("label", ""),
        "summary": chunk_meta.get("summary", ""),
        "content": raw_content,
        "key_concepts": chunk_meta.get("keywords", []),
    }


async def generate_outlines(chapter_id: str | None = None) -> dict:
    """Step 1: Select random chunk × dimension, generate 5 outlines.

    Returns:
        {
            "outlines": ["outline 1 text", ...],  # list of 5
            "chunk_data": {...},
            "chunk_id": "C5-01",
            "dimension": "PAIN",
            "raw_response": "...",
        }
    """
    chunk_map = await fetch_chunk_map(chapter_id)
    chunk_ids = extract_chunk_ids(chunk_map)

    if not chunk_ids:
        raise ValueError("Chunk map returned no chunk IDs.")

    chunk_id = random.choice(chunk_ids)
    dimension = random.choice(DIMENSIONS)
    logger.info("Selected combination: chunk_id=%s, dimension=%s", chunk_id, dimension)

    chunk_data = await _build_chunk_data(chunk_id, chunk_map)

    client = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY", ""))
    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS_OUTLINES,
        system=build_outlines_system_prompt(dimension, chunk_data),
        messages=[{"role": "user", "content": build_outlines_user_message(dimension, chunk_id)}],
    )

    raw_response = message.content[0].text if message.content else ""

    # Parse 5 outlines split by ===OUTLINE===
    parts = [p.strip() for p in raw_response.split("===OUTLINE===") if p.strip()]
    outlines = parts[:5]  # take up to 5

    # Pad with empty string if Claude returned fewer
    while len(outlines) < 5:
        outlines.append("")

    logger.info("Parsed %d outlines from response", len([o for o in outlines if o]))

    return {
        "outlines": outlines,
        "chunk_data": chunk_data,
        "chunk_id": chunk_id,
        "dimension": dimension,
        "raw_response": raw_response,
    }


async def generate_full_article(outline: str, chunk_data: dict, dimension: str, style_data: dict) -> str:
    """Step 2: Generate a full article from a selected outline + style guide.

    Returns the article text ready for Telegram.
    """
    client = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY", ""))
    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS_ARTICLE,
        system=build_full_article_system_prompt(style_data, chunk_data, dimension),
        messages=[{"role": "user", "content": build_full_article_user_message(outline)}],
    )

    return message.content[0].text if message.content else ""
