"""GitHub knowledge file fetcher."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GITHUB_RAW_BASE_URL = os.getenv("GITHUB_RAW_BASE_URL", "")

CHUNK_MAP_PATH = "chunks/chapter5_chunks.json"


async def fetch_chunk_map() -> dict:
    """Fetch the chunk map JSON from GitHub."""
    url = f"{GITHUB_RAW_BASE_URL.rstrip('/')}/{CHUNK_MAP_PATH}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def fetch_knowledge_file(chunk_id: str) -> dict:
    """Fetch a specific knowledge file from GitHub by chunk_id."""
    url = f"{GITHUB_RAW_BASE_URL.rstrip('/')}/knowledge/{chunk_id}.json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def extract_chunk_ids(chunk_map: dict) -> list[str]:
    """Extract all chunk IDs from the chunk map.

    Supports chunk map formats:
      - {"chunks": ["c1", "c2", ...]}
      - {"chunks": [{"id": "c1"}, ...]}
      - ["c1", "c2", ...]
      - {"c1": {...}, "c2": {...}}  (dict keyed by chunk_id)
    """
    if isinstance(chunk_map, list):
        return [item["id"] if isinstance(item, dict) else item for item in chunk_map]

    if "chunks" in chunk_map:
        chunks = chunk_map["chunks"]
        return [item["id"] if isinstance(item, dict) else item for item in chunks]

    # Assume keys are chunk IDs
    return list(chunk_map.keys())
