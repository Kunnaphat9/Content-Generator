"""Content generation logic: selects chunk × dimension, calls Claude API."""

import logging
import os
import random

import anthropic

from knowledge import extract_chunk_ids, fetch_chunk_map, fetch_knowledge_file, get_chunk_metadata
from prompts import DIMENSIONS, build_system_prompt, build_user_message

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500


async def generate_content() -> str:
    """Full pipeline: select combination → fetch knowledge → call Claude."""
    # 1. Fetch chunk map
    chunk_map = await fetch_chunk_map()
    chunk_ids = extract_chunk_ids(chunk_map)

    if not chunk_ids:
        raise ValueError("Chunk map returned no chunk IDs.")

    # 2. Pick random combination
    chunk_id = random.choice(chunk_ids)
    dimension = random.choice(DIMENSIONS)
    logger.info("Selected combination: chunk_id=%s, dimension=%s", chunk_id, dimension)

    # 3. Fetch knowledge file
    raw_knowledge = await fetch_knowledge_file(chunk_id)
    chunk_meta = get_chunk_metadata(chunk_map, chunk_id)

    # 4. Normalize content
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

    chunk_data = {
        "title": chunk_meta.get("label") or raw_knowledge.get("label", ""),
        "summary": chunk_meta.get("summary", ""),
        "content": raw_content,
        "key_concepts": chunk_meta.get("keywords", []),
    }

    # 5. Call Claude API
    client = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY", ""))
    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=build_system_prompt(dimension, chunk_data),
        messages=[{"role": "user", "content": build_user_message(dimension, chunk_id)}],
    )

    result_text = message.content[0].text if message.content else ""

    # 6. Format response for Telegram
    header = (
        f"📊 *Elliott Wave Content*\n"
        f"Chunk: `{chunk_id}` | Dimension: `{dimension}`\n"
        f"{'─' * 30}\n\n"
    )
    return header + result_text
