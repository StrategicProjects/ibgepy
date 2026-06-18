"""In-memory, per-session caches (equivalent to the R package's environments).

Two stores mirror ``.ibger_cache`` and ``.ibger_survey_cache``:

* :data:`_AGG_META_CACHE` holds aggregate listings and aggregate metadata.
* :data:`_SURVEY_CACHE` holds the survey catalog and per-survey periods.
"""
from __future__ import annotations

from typing import Any, Dict

_AGG_META_CACHE: Dict[str, Any] = {}
_SURVEY_CACHE: Dict[str, Any] = {}


def clear_cache() -> None:
    """Remove all cached metadata (aggregates and surveys).

    Forces fresh API calls on subsequent requests. Public alias:
    :func:`ibgepy.ibge_clear_cache`.
    """
    _AGG_META_CACHE.clear()
    _SURVEY_CACHE.clear()
    from . import _msg

    _msg.success("Metadata cache cleared.")
