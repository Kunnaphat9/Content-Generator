"""Content generation logic: selects chunk × dimension, calls Claude API."""

import logging
import os
import random

import anthropic

from knowledge import extract_chunk_ids, fetch_chunk_map, fetch_knowledge_file
from logger import get_used_combinations, log_combination
from prompts import DIMENSIONS, build_system_prompt, build_user_message

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500


def _build_all_combinations(chunk_ids: list[str]) -> list[tuple[str, str]]:
    return [(chunk_id, dim) for chunk_id in chunk_ids for dim in DIMENSIONS]


def _pick_combination(
    all_combinations: list[tuple[str, str]],
    used: list[tuple[str, str]],
) -> tuple[str, str] | None:
    used_set = set(used)
    available = [c for c in all_combinations if c not in used_set]

    if not available:
        logger.warning("All combinations have been used. Resetting pool.")
        # Fall back to any random combination when all are exhausted
        available = all_combinations

    return random.choice(available) if available else None


async def generate_content() -> str:
    """Full pipeline: select combination → fetch knowledge → call Claude → log."""
    # 1. Fetch chunk map and used combinations in parallel context
    chunk_map = await fetch_chunk_map()
    chunk_ids = extract_chunk_ids(chunk_map)

    if not chunk_ids:
        raise ValueError("Chunk map returned no chunk IDs.")

    used = await get_used_combinations()

    # 2. Pick unused combination
    all_combinations = _build_all_combinations(chunk_ids)
    selection = _pick_combination(all_combinations, used)

    if selection is None:
        raise RuntimeError("Could not select a chunk × dimension combination.")

    chunk_id, dimension = selection
    logger.info("Selected combination: chunk_id=%s, dimension=%s", chunk_id, dimension)

    # 3. Fetch knowledge file for selected chunk
    chunk_data = await fetch_knowledge_file(chunk_id)

    # 4. Build prompts
    system_prompt = build_system_prompt(dimension, chunk_data)
    user_message = build_user_message(dimension, chunk_id)

    # 5. Call Claude API
    client = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY", ""))
    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    result_text = message.content[0].text if message.content else ""

    # 6. Log the combination to DB
    await log_combination(chunk_id, dimension)

    # 7. Format response for Telegram
    header = (
        f"📊 *Elliott Wave Content*\n"
        f"Chunk: `{chunk_id}` | Dimension: `{dimension}`\n"
        f"{'─' * 30}\n\n"
    )
    return header + result_text
