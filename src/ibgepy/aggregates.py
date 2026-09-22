"""List IBGE aggregates (SIDRA tables), grouped by survey."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

import pandas as pd

from . import _cache, _msg
from ._client import ibge_request
from ._format import pluck_str


def _cache_key(params: dict) -> str:
    blob = json.dumps(params, sort_keys=True, default=str)
    return "aggregates_" + hashlib.sha1(blob.encode("utf-8")).hexdigest()


# Periodicity codes observed in the catalog (the API has no lookup endpoint).
PERIODICITIES = {
    "P1": "annual",
    "P5": "monthly",
    "P7": "every three years",
    "P8": "semi-annual",
    "P9": "quarterly",
    "P11": "every two years",
    "P13": "rolling quarter (PNAD Contínua)",
    "P16": "every six years",
}

_FILTER_PATTERNS = {
    "subject": (r"^[0-9]+$", "70"),
    "classification": (r"^[0-9]+$", "12026"),
    "periodicity": (r"^P[0-9]+$", "P5"),
    "level": (r"^N[0-9]+$", "N3"),
    "period": (r"^P[0-9]+\[[0-9]+(,[0-9]+)*\]$", "P5[202001]"),
}


def _check_filter(value: Any, arg: str) -> None:
    """Raise ValueError unless ``value`` is None or matches the API syntax.

    The API silently drops filters it cannot parse (returning the whole
    catalog) and answers HTTP 500 to some values (e.g. ``periodicity=30``),
    so the format is checked before the request.
    """
    if value is None:
        return
    pattern, example = _FILTER_PATTERNS[arg]
    ok = isinstance(value, (str, int)) and not isinstance(value, bool) and re.match(
        pattern, str(value)
    )
    if not ok:
        raise ValueError(
            f"Invalid `{arg}` filter: {value!r}. Expected a single value like "
            f"{example!r}; see help(ibge_aggregates) for the accepted formats."
        )


def ibge_aggregates(
    period: Optional[str] = None,
    subject: Optional[int] = None,
    classification: Optional[int] = None,
    periodicity: Optional[str] = None,
    level: Optional[str] = None,
) -> pd.DataFrame:
    """List available aggregates (tables), optionally filtered.

    Results are cached in memory per unique parameter combination.

    Parameters
    ----------
    period
        Periodicity code followed by one or more period ids in brackets,
        e.g. ``"P5[202001]"`` or ``"P1[2019,2020]"``.
    subject
        Numeric subject code (see :func:`ibge_subjects`), e.g. ``70``.
    classification
        Numeric classification code, e.g. ``12026``.
    periodicity
        Periodicity code: ``"P1"`` (annual), ``"P5"`` (monthly), ``"P8"``
        (semi-annual), ``"P9"`` (quarterly), ``"P13"`` (rolling quarter);
        see :data:`PERIODICITIES` for the codes observed in the catalog.
    level
        Geographic level: ``"N1"`` (Brazil), ``"N3"`` (state), ``"N6"``
        (municipality), ...

    All filters are checked for the format the API expects before the
    request, because the API ignores what it cannot parse (returning the
    whole catalog) or answers HTTP 500. A well-formed filter that matches no
    aggregate returns an empty DataFrame with a warning.

    Returns a DataFrame with columns ``survey_id``, ``survey_name``,
    ``aggregate_id``, ``aggregate_name``.
    """
    for name, value in (
        ("period", period),
        ("subject", subject),
        ("classification", classification),
        ("periodicity", periodicity),
        ("level", level),
    ):
        _check_filter(value, name)

    params = {
        "periodo": period,
        "assunto": subject,
        "classificacao": classification,
        "periodicidade": periodicity,
        "nivel": level,
    }
    key = _cache_key(params)
    cached = _cache._AGG_META_CACHE.get(key)
    if cached is not None:
        _msg.success(f"{len(cached)} aggregate(s) found (cached).")
        return cached

    query = {k: v for k, v in params.items() if v is not None}
    data = ibge_request(query=query, label="aggregates")

    rows = []
    for survey in data:
        aggregates = survey.get("agregados") or []
        for ag in aggregates:
            rows.append(
                {
                    "survey_id": pluck_str(survey, "id"),
                    "survey_name": pluck_str(survey, "nome"),
                    "aggregate_id": pluck_str(ag, "id"),
                    "aggregate_name": pluck_str(ag, "nome"),
                }
            )

    result = pd.DataFrame(
        rows, columns=["survey_id", "survey_name", "aggregate_id", "aggregate_name"]
    )
    _cache._AGG_META_CACHE[key] = result
    if len(result) == 0:
        _msg.warn("No aggregates found for the given filters.")
    else:
        _msg.success(f"{len(result)} aggregate(s) found.")
    return result
