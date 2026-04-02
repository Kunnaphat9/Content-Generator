"""GitHub knowledge file fetcher."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GITHUB_RAW_BASE_URL = os.getenv("GITHUB_RAW_BASE_URL", "")

CHUNK_MAP_PATH = "chunks/chapter5_chunks.json"


def _github_headers() -> dict:
    """Return auth headers for GitHub. Works for both public and private repos."""
    token = os.getenv("GITHUB_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


async def fetch_chunk_map() -> dict:
    """Fetch the chunk map JSON from GitHub."""
    url = f"{GITHUB_RAW_BASE_URL.rstrip('/')}/{CHUNK_MAP_PATH}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=_github_headers())
        response.raise_for_status()
        return response.json()


async def fetch_knowledge_file(chunk_id: str) -> dict:
    """Fetch a specific knowledge file from GitHub by chunk_id."""
    url = f"{GITHUB_RAW_BASE_URL.rstrip('/')}/knowledge/{chunk_id}.json"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=_github_headers())
        response.raise_for_status()
        return response.json()


def extract_chunk_ids(chunk_map: dict) -> list[str]:
    """Extract all chunk IDs from the chunk map.

    Supports chunk map formats:
      - {"chunks": [{"chunk_id": "C5-01"}, ...]}   ← actual format
      - {"chunks": [{"id": "c1"}, ...]}
      - {"chunks": ["c1", "c2", ...]}
      - ["c1", "c2", ...]
      - {"c1": {...}, "c2": {...}}  (dict keyed by chunk_id)
    """
    def _id_from(item):
        if isinstance(item, dict):
            return item.get("chunk_id") or item.get("id") or ""
        return item

    if isinstance(chunk_map, list):
        return [_id_from(item) for item in chunk_map]

    if "chunks" in chunk_map:
        return [_id_from(item) for item in chunk_map["chunks"]]

    # Assume keys are chunk IDs
    return list(chunk_map.keys())


def get_chunk_metadata(chunk_map: dict, chunk_id: str) -> dict:
    """Return the chunk map entry for a given chunk_id, or empty dict."""
    chunks = chunk_map.get("chunks", [])
    for item in chunks:
        if isinstance(item, dict):
            if item.get("chunk_id") == chunk_id or item.get("id") == chunk_id:
                return item
    return {}
