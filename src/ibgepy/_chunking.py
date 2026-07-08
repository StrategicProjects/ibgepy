"""Automatic splitting of large queries (port of the R package's chunking.R).

The IBGE API rejects requests whose result is too large with an HTTP 500
error. The documented limit is 100,000 values, but empirically requests fail
above ~50,000 values (e.g. 44,560 values -> HTTP 200; 50,130 -> HTTP 500).
:func:`build_chunk_plan` estimates the result size (variables x periods x
localities x category combinations) and, when it exceeds the limit, plans a
sequence of smaller requests: first splitting periods, then localities when
a single period is still too large.
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Mapping, Optional

from . import _cache, _msg
from ._client import ibge_request
from ._format import format_localities, pluck_str
from .metadata import IbgeMetadata, get_cached_metadata
from .validation import extract_numeric_periods

# Value limit enforced by the IBGE API on a single request (see module docs).
IBGE_VALUE_LIMIT = 50000

# Cap on locality ids per request to keep URLs at a safe length.
MAX_LOCALITIES_PER_REQUEST = 500


def resolve_chunk_limit(chunk: Any) -> Optional[float]:
    """Resolve the ``chunk`` argument into a per-request value limit.

    ``True`` -> API limit, ``False`` -> ``None`` (disabled), positive number
    -> custom limit.
    """
    if chunk is False:
        return None
    if chunk is True:
        return IBGE_VALUE_LIMIT
    if isinstance(chunk, (int, float)) and chunk > 0:
        return float(chunk)
    raise ValueError(
        "`chunk` must be True, False or a positive number. "
        f"Use True to split queries above the API limit of {IBGE_VALUE_LIMIT} values."
    )


def get_cached_period_ids(aggregate: int) -> List[str]:
    """Period ids available for an aggregate (cached per session)."""
    cache_key = f"period_ids_{aggregate}"
    cached = _cache._AGG_META_CACHE.get(cache_key)
    if cached is not None:
        return cached

    data = ibge_request(
        aggregate, "periodos", label=f"period list for aggregate {aggregate}"
    )
    ids = [pluck_str(p, "id") for p in data or []]
    ids = [i for i in ids if i is not None]

    _cache._AGG_META_CACHE[cache_key] = ids
    return ids


def get_cached_locality_ids(aggregate: int, level: str) -> List[str]:
    """Locality ids for an aggregate at a level (cached per session)."""
    cache_key = f"locality_ids_{aggregate}_{level}"
    cached = _cache._AGG_META_CACHE.get(cache_key)
    if cached is not None:
        return cached

    data = ibge_request(
        aggregate, "localidades", level,
        label=f"{level} localities for aggregate {aggregate}",
    )
    ids = [pluck_str(loc, "id") for loc in data or []]
    ids = [i for i in ids if i is not None]

    _cache._AGG_META_CACHE[cache_key] = ids
    return ids


def estimate_n_variables(get_meta: Callable[[], IbgeMetadata], variable: Any) -> int:
    """Estimated number of variables in the result.

    ``get_meta`` is a zero-argument callable so metadata is only fetched when
    actually needed.
    """
    if variable is None or variable == "allxp":
        return max(1, len(get_meta().variables))
    if variable in ("all", "todas"):
        # "all" adds auto-generated percentage variables; assume up to twice.
        return max(1, 2 * len(get_meta().variables))
    if isinstance(variable, (list, tuple)):
        return len(variable)
    return 1


def estimate_n_categories(
    get_meta: Callable[[], IbgeMetadata], classification: Any
) -> int:
    """Estimated number of category combinations in the result.

    Without ``classificacao`` the API returns only the "Total" combination,
    so the default is 1.
    """
    if not classification or not isinstance(classification, Mapping):
        return 1

    total = 1
    for cls_id, cats in classification.items():
        if cats in ("all", "todos"):
            cls = get_meta().classifications
            match = cls[cls["id"] == str(cls_id)]
            if len(match) == 0:
                count = 1
            else:
                count = max(1, len(match["categories"].iloc[0]))
        elif isinstance(cats, (list, tuple)):
            count = len(cats)
        else:
            count = 1
        total *= count
    return total


def estimate_n_periods(periods: Any) -> int:
    """Estimated number of periods (without hitting the API)."""
    if periods is None:
        return 6
    if isinstance(periods, int) and periods < 0:
        return abs(periods)
    if isinstance(periods, str) and re.fullmatch(r"-\d+", periods.strip()):
        return abs(int(periods))
    n_numeric = len(extract_numeric_periods(periods))
    n_given = len(periods) if isinstance(periods, (list, tuple)) else 1
    return max(n_numeric, n_given)


def resolve_period_ids(aggregate: int, periods: Any) -> List[str]:
    """Resolve the concrete period ids requested (may hit the API)."""
    all_ids = get_cached_period_ids(aggregate)

    if periods is None:
        periods = -6

    is_last_n = (isinstance(periods, int) and periods < 0) or (
        isinstance(periods, str) and re.fullmatch(r"-\d+", periods.strip())
    )
    if is_last_n:
        n = min(abs(int(periods)), len(all_ids))
        return all_ids[-n:] if n > 0 else []

    requested = {str(int(p)) for p in extract_numeric_periods(periods)}
    ids = [i for i in all_ids if i in requested]

    if not ids:
        # Unrecognized form: keep the values as given.
        parts = periods if isinstance(periods, (list, tuple)) else [periods]
        ids = [seg for part in parts for seg in str(part).split("|")]

    return ids


def resolve_localities_for_chunking(aggregate: int, localities: Any) -> Dict[str, Any]:
    """Resolve localities into countable units for chunking.

    Returns ``{"n": count, "units": [(level, id), ...] or None}`` where
    ``units`` is ``None`` when the localities cannot be enumerated
    (e.g. ``"BR"`` or an unrecognized format).
    """
    if isinstance(localities, str):
        localities = [localities]

    if isinstance(localities, (list, tuple)) and all(
        isinstance(x, str) for x in localities
    ):
        codes = [x.upper() for x in localities]
        if len(codes) == 1 and codes[0] == "BR":
            return {"n": 1, "units": None}
        if all(re.fullmatch(r"N\d+", c) for c in codes):
            units = [
                (level, loc_id)
                for level in codes
                for loc_id in get_cached_locality_ids(aggregate, level)
            ]
            return {"n": len(units), "units": units}
        return {"n": 1, "units": None}

    if isinstance(localities, Mapping):
        units = []
        for level, ids in localities.items():
            ids_list = ids if isinstance(ids, (list, tuple)) else [ids]
            units.extend((level, str(i)) for i in ids_list)
        return {"n": len(units), "units": units}

    return {"n": 1, "units": None}


def units_to_localities_str(units: List[tuple]) -> str:
    """Format ``(level, id)`` units back into the API localities syntax."""
    by_level: Dict[str, List[str]] = {}
    for level, loc_id in units:
        by_level.setdefault(level, []).append(loc_id)
    parts = [f"{level}[{','.join(ids)}]" for level, ids in by_level.items()]
    return "|".join(parts)


def split_in_groups(items: List[Any], size: int) -> List[List[Any]]:
    """Split a list into consecutive groups of at most ``size`` elements."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def build_chunk_plan(
    aggregate: int,
    meta: Optional[IbgeMetadata],
    variable: Any,
    periods: Any,
    localities: Any,
    classification: Any,
    limit: float,
) -> Optional[List[Dict[str, str]]]:
    """Plan how to split a query that exceeds the API value limit.

    ``meta`` may be ``None``; it is fetched lazily only when needed. Returns
    ``None`` when a single request fits within ``limit``; otherwise a list of
    chunks, each a dict with ``periods_str`` and ``localities_str``.
    """
    state = {"meta": meta}

    def get_meta() -> IbgeMetadata:
        if state["meta"] is None:
            state["meta"] = get_cached_metadata(aggregate)
        return state["meta"]

    n_var = estimate_n_variables(get_meta, variable)
    n_cat = estimate_n_categories(get_meta, classification)

    loc = resolve_localities_for_chunking(aggregate, localities)
    base = n_var * n_cat * loc["n"]

    if base * estimate_n_periods(periods) <= limit:
        return None

    per_ids = resolve_period_ids(aggregate, periods)
    if base * len(per_ids) <= limit:
        return None

    # 1) Split periods: each chunk keeps the original localities.
    p_max = math.floor(limit / base)
    if p_max >= 1:
        localities_str = format_localities(localities)
        return [
            {"periods_str": "|".join(group), "localities_str": localities_str}
            for group in split_in_groups(per_ids, p_max)
        ]

    # 2) A single period still exceeds the limit: split localities as well.
    if loc["units"] is None:
        _msg.warn(
            f"A single period may still exceed the API limit of {limit:.0f} "
            "values and the localities cannot be subdivided. "
            "Consider reducing variables or classification categories."
        )
        localities_str = format_localities(localities)
        return [
            {"periods_str": p, "localities_str": localities_str} for p in per_ids
        ]

    per_loc = n_var * n_cat
    if per_loc > limit:
        _msg.warn(
            f"A single period and locality may still exceed the API limit of "
            f"{limit:.0f} values. Consider reducing variables or "
            "classification categories."
        )

    l_max = max(1, min(math.floor(limit / per_loc), MAX_LOCALITIES_PER_REQUEST))
    return [
        {"periods_str": p, "localities_str": units_to_localities_str(group)}
        for p in per_ids
        for group in split_in_groups(loc["units"], l_max)
    ]
