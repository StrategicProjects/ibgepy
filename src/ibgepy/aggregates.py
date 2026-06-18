"""List IBGE aggregates (SIDRA tables), grouped by survey."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import pandas as pd

from . import _cache, _msg
from ._client import ibge_request
from ._format import pluck_str


def _cache_key(params: dict) -> str:
    blob = json.dumps(params, sort_keys=True, default=str)
    return "aggregates_" + hashlib.sha1(blob.encode("utf-8")).hexdigest()


def ibge_aggregates(
    period: Optional[str] = None,
    subject: Optional[int] = None,
    classification: Optional[int] = None,
    periodicity: Optional[str] = None,
    level: Optional[str] = None,
) -> pd.DataFrame:
    """List available aggregates (tables), optionally filtered.

    Results are cached in memory per unique parameter combination.

    Returns a DataFrame with columns ``survey_id``, ``survey_name``,
    ``aggregate_id``, ``aggregate_name``.
    """
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
    _msg.success(f"{len(result)} aggregate(s) found.")
    return result
