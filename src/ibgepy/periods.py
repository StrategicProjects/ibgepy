"""Available periods for an aggregate."""
from __future__ import annotations

import pandas as pd

from . import _msg
from ._client import ibge_request
from ._format import pluck_str


def ibge_periods(aggregate: int) -> pd.DataFrame:
    """Retrieve available periods for an aggregate.

    Returns a DataFrame with columns ``id``, ``literal``, ``modification``.
    """
    data = ibge_request(aggregate, "periodos", label=f"periods for aggregate {aggregate}")

    rows = []
    for p in data:
        lits = p.get("literals") or []
        lit_str = " / ".join(str(x) for x in lits) if lits else None
        rows.append(
            {
                "id": pluck_str(p, "id"),
                "literal": lit_str,
                "modification": pluck_str(p, "modificacao"),
            }
        )

    result = pd.DataFrame(rows, columns=["id", "literal", "modification"])
    _msg.success(f"{len(result)} period(s) found.")
    return result
