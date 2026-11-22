"""Shared path helpers for crawler caches and annotation workflows.

Upstream-managed: see `documents/crawler_conventions.md` and
`documents/annotation_conventions.md`. Register instance-specific cache
directories in your own code, e.g. `MY_CACHE_DIR = cache_dir("my_feature")`.
"""

from __future__ import annotations

from pathlib import Path

PANEL_FACTORY_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PANEL_FACTORY_ROOT / "data"
CACHE_DIR = DATA_ROOT / ".cache"


def cache_dir(feature_name: str) -> Path:
    """Return the cache directory for one feature: `data/.cache/<feature_name>/`."""
    return CACHE_DIR / feature_name


def cache_store_path(feature_name: str, store_name: str | None = None) -> Path:
    """Return the sqlite store path for one feature."""
    return cache_dir(feature_name) / (store_name or f"{feature_name}_store.sqlite")


def annotation_temp_dir(feature_name: str) -> Path:
    """Return the TEMP directory for one annotation workflow."""
    return DATA_ROOT / "TEMP" / "features" / feature_name
