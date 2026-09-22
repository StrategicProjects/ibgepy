"""Localities for an aggregate at one or more geographic levels."""
from __future__ import annotations

from typing import Sequence, Union

import pandas as pd

from . import _msg
from ._client import ibge_request
from ._format import pluck_str
from .validation import get_cached_metadata, validate_query


def ibge_localities(
    aggregate: int,
    level: Union[str, Sequence[str]] = "N6",
    validate: bool = True,
) -> pd.DataFrame:
    """Retrieve available localities for an aggregate.

    ``level`` may be a single level (``"N6"``) or a list (``["N6", "N7"]``).
    With several levels one request is made per level and the results are
    concatenated: the API's own multi-level endpoint returns an empty list
    as soon as one of the levels has no localities for the aggregate.

    Returns a DataFrame with columns ``id``, ``name``, ``level_id``,
    ``level_name`` (empty, but with those columns, when nothing is found).
    """
    if validate:
        meta = get_cached_metadata(aggregate)
        validate_query(meta, level=level)

    levels = [level] if isinstance(level, str) else list(level)

    rows = []
    for lvl in levels:
        data = ibge_request(
            aggregate, "localidades", lvl, label=f"{lvl} localities for aggregate {aggregate}"
        )
        rows.extend(
            {
                "id": pluck_str(loc, "id"),
                "name": pluck_str(loc, "nome"),
                "level_id": pluck_str(loc, "nivel", "id"),
                "level_name": pluck_str(loc, "nivel", "nome"),
            }
            for loc in data
        )
    result = pd.DataFrame(rows, columns=["id", "name", "level_id", "level_name"])
    if len(result) == 0:
        _msg.warn(f"No localities found for aggregate {aggregate} at level {levels}.")
    else:
        _msg.success(f"{len(result)} localit(y/ies) found.")
    return result
