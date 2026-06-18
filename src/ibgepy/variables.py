"""The main entry point: fetch variable results for an aggregate (tidy long)."""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Union

import pandas as pd

from . import _msg
from ._client import ibge_request
from ._format import (
    format_classification,
    format_localities,
    format_periods,
    format_variable,
    pluck_str,
)
from .validation import get_cached_metadata, validate_query

Localities = Union[str, Sequence[str], Mapping[str, Any]]


def ibge_variables(
    aggregate: int,
    variable: Any = None,
    periods: Any = -6,
    localities: Localities = "BR",
    classification: Optional[Mapping[str, Any]] = None,
    view: Optional[str] = None,
    validate: bool = True,
) -> pd.DataFrame:
    """Retrieve variable results from an aggregate (the package's main function).

    Parameters
    ----------
    aggregate:
        Numeric aggregate identifier (SIDRA table).
    variable:
        ``None`` (default standard variables), an id or list of ids, or
        ``"all"`` (include generated percentage variables).
    periods:
        Negative int for last-N (default ``-6``), a value/list, or a range
        string like ``"201701-201712"``.
    localities:
        ``"BR"`` (default), a level code (``"N3"``), or a mapping such as
        ``{"N6": [3550308, 3304557]}``.
    classification:
        Mapping of classification id -> category id(s), or ``"all"``.
    view:
        ``None`` (default), ``"OLAP"`` or ``"flat"``.
    validate:
        If ``True`` (default), validate parameters against the aggregate
        metadata before querying.

    Returns
    -------
    pandas.DataFrame
        Tidy (long) format: ``variable_id``, ``variable_name``,
        ``variable_unit``, classification columns (when present),
        ``locality_id``, ``locality_name``, ``locality_level``, ``period``,
        ``value`` (string; use :func:`ibgepy.parse_ibge_value`).
    """
    if validate:
        meta = get_cached_metadata(aggregate)
        validate_query(
            meta,
            localities=localities,
            periods=periods,
            variable=variable,
            classification=classification,
        )

    variable_str = format_variable(variable)
    periods_str = format_periods(periods)
    localities_str = format_localities(localities)
    classification_str = format_classification(classification)

    query = {
        "localidades": localities_str,
        "classificacao": classification_str,
        "view": view,
    }

    data = ibge_request(
        aggregate,
        "periodos",
        periods_str,
        "variaveis",
        variable_str,
        query=query,
        label=f"variables for aggregate {aggregate}",
    )

    result = _parse_variables(data, view=view)
    _msg.success(f"{len(result)} record(s) retrieved.")
    return result


def _parse_variables(data: Any, view: Optional[str] = None) -> pd.DataFrame:
    if not data:
        return pd.DataFrame()
    first = data[0]
    is_flat = first.get("NC") is not None and first.get("V") is not None
    return _parse_flat(data) if is_flat else _parse_default(data)


def _parse_flat(data: list) -> pd.DataFrame:
    """Flat view: first element is a header row, the rest are data rows."""
    if len(data) < 2:
        return pd.DataFrame()
    header, rows = data[0], data[1:]
    keys = list(header.keys())
    col_map = {k: (str(header[k]) if header.get(k) is not None else k) for k in keys}

    records = []
    for row in rows:
        record = {}
        for k in keys:
            val = row.get(k)
            record[col_map[k]] = None if val is None else str(val)
        records.append(record)
    return pd.DataFrame(records)


def _parse_classifications(classifications: Any) -> dict:
    """Return a single-row dict of classification_<id> -> category name."""
    cols = {}
    for cls in classifications or []:
        cls_id = pluck_str(cls, "id")
        cat_obj = cls.get("categoria") or {}
        # `categoria` is a mapping {category_id: category_name}; take first value.
        cat_name = None
        if isinstance(cat_obj, Mapping) and cat_obj:
            cat_name = str(next(iter(cat_obj.values())))
        cols[f"classification_{cls_id}"] = cat_name
    return cols


def _parse_default(data: list) -> pd.DataFrame:
    rows = []
    for var in data:
        var_id = pluck_str(var, "id")
        var_name = pluck_str(var, "variavel")
        var_unit = pluck_str(var, "unidade")

        for res in var.get("resultados") or []:
            cls_cols = _parse_classifications(res.get("classificacoes"))
            for serie in res.get("series") or []:
                loc = serie.get("localidade") or {}
                loc_id = pluck_str(loc, "id")
                loc_name = pluck_str(loc, "nome")
                loc_level = pluck_str(loc, "nivel", "nome")

                serie_data = serie.get("serie") or {}
                for period, value in serie_data.items():
                    row = {
                        "variable_id": var_id,
                        "variable_name": var_name,
                        "variable_unit": var_unit,
                        **cls_cols,
                        "locality_id": loc_id,
                        "locality_name": loc_name,
                        "locality_level": loc_level,
                        "period": period,
                        "value": None if value is None else str(value),
                    }
                    rows.append(row)

    return pd.DataFrame(rows)
