"""GitHub knowledge file fetcher."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GITHUB_RAW_BASE_URL = os.getenv("GITHUB_RAW_BASE_URL", "")


def _parse_raw_url(raw_base: str) -> tuple[str, str, str] | None:
    """Parse owner, repo, ref from a raw.githubusercontent.com base URL.

    e.g. https://raw.githubusercontent.com/Org/Repo/my/branch
    →  ("Org", "Repo", "my/branch")
    """
    prefix = "https://raw.githubusercontent.com/"
    if not raw_base.startswith(prefix):
        return None
    parts = raw_base[len(prefix):].rstrip("/").split("/", 2)
    if len(parts) < 3:
        return None
    return parts[0], parts[1], parts[2]


async def _fetch_file(path: str) -> dict:
    """Fetch a JSON file from GitHub, using the Contents API when a token is set."""
    token = os.getenv("GITHUB_TOKEN", "")
    parsed = _parse_raw_url(GITHUB_RAW_BASE_URL)

    if token and parsed:
        # GitHub Contents API — works reliably for private repos
        owner, repo, ref = parsed
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.raw",  # returns raw bytes, not base64
        }
        logger.info("Fetching via GitHub API: %s (ref=%s)", path, ref)
    else:
        # No token — public repo, use raw URL directly
        url = f"{GITHUB_RAW_BASE_URL.rstrip('/')}/{path}"
        headers = {}
        logger.info("Fetching via raw URL: %s", url)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


CHUNK_MAP_PATHS = [
    "chunks/chapter1_chunks.json",
    "chunks/chapter5_chunks.json",
]


def _chapter_id_from_path(path: str) -> str:
    """'chunks/chapter1_chunks.json' → 'chapter1'"""
    return path.split("/")[-1].replace("_chunks.json", "")


_chapter_list_cache: list | None = None


async def fetch_chapter_list() -> list[dict]:
    """Fetch and cache metadata for all available chapters.

    Returns list of dicts: {id, chapter, title, chunk_count}
    """
    global _chapter_list_cache
    if _chapter_list_cache is not None:
        return _chapter_list_cache

    result = []
    for path in CHUNK_MAP_PATHS:
        try:
            chunk_map = await _fetch_file(path)
            result.append({
                "id": _chapter_id_from_path(path),
                "chapter": chunk_map.get("chapter", "?"),
                "title": chunk_map.get("chapter_title", ""),
                "chunk_count": len(chunk_map.get("chunks", [])),
            })
            logger.info("Chapter loaded: %s — %s", chunk_map.get("chapter"), chunk_map.get("chapter_title"))
        except Exception as e:
            logger.warning("Could not load chapter info from %s: %s", path, e)

    _chapter_list_cache = result
    return result


async def fetch_chunk_map(chapter_id: str | None = None) -> dict:
    """Fetch chunk map(s). If chapter_id given, only load that chapter."""
    all_chunks = []
    for path in CHUNK_MAP_PATHS:
        if chapter_id and _chapter_id_from_path(path) != chapter_id:
            continue
        try:
            chunk_map = await _fetch_file(path)
            all_chunks.extend(chunk_map.get("chunks", []))
            logger.info("Loaded %d chunks from %s", len(chunk_map.get("chunks", [])), path)
        except Exception as e:
            logger.warning("Could not load chunk map %s: %s", path, e)
    return {"chunks": all_chunks}


async def fetch_knowledge_file(chunk_id: str) -> dict:
    """Fetch a specific knowledge file from GitHub by chunk_id."""
    return await _fetch_file(f"knowledge/{chunk_id}.json")


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


_style_guide_cache: dict | None = None


async def fetch_style_guide() -> dict:
    """Fetch and cache the style.json voice guide from GitHub."""
    global _style_guide_cache
    if _style_guide_cache is None:
        _style_guide_cache = await _fetch_file("knowledge/style.json")
    return _style_guide_cache
