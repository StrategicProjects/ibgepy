"""Aggregate metadata: variables, classifications, categories and levels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd

from . import _cache, _msg
from ._client import ibge_request
from ._format import pluck, pluck_str


@dataclass
class IbgeMetadata:
    """Complete metadata for an IBGE aggregate.

    ``classifications`` is a DataFrame whose ``categories`` column holds, for
    each row, a nested DataFrame of categories (the equivalent of the R
    list-column).
    """

    id: Any
    name: Any
    url: Any
    survey: Any
    subject: Any
    periodicity: Dict[str, Any]
    territorial_level: Dict[str, List[str]]
    variables: pd.DataFrame
    classifications: pd.DataFrame

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        n_vars = len(self.variables)
        n_cls = len(self.classifications)
        n_cats = int(sum(len(c) for c in self.classifications["categories"])) if n_cls else 0
        return (
            f"<IbgeMetadata {self.id}: {self.name!r} | "
            f"{n_vars} variables, {n_cls} classifications, {n_cats} categories>"
        )


def _empty_categories() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["category_id", "category_name", "category_unit", "category_level"]
    )


def ibge_metadata(aggregate: int) -> IbgeMetadata:
    """Retrieve complete metadata for an aggregate (cached per session)."""
    cache_key = f"meta_{aggregate}"
    cached = _cache._AGG_META_CACHE.get(cache_key)
    if cached is not None:
        _report(cached, aggregate, cached_flag=True)
        return cached

    data = ibge_request(aggregate, "metadados", label=f"metadata for aggregate {aggregate}")
    if isinstance(data, list) and len(data) >= 1:
        data = data[0]

    # --- Variables ---
    vars_raw = data.get("variaveis") or []
    if vars_raw:
        variables = pd.DataFrame(
            [
                {
                    "id": pluck_str(v, "id"),
                    "name": pluck_str(v, "nome"),
                    "unit": pluck_str(v, "unidade"),
                }
                for v in vars_raw
            ]
        )
    else:
        variables = pd.DataFrame(columns=["id", "name", "unit"])

    # --- Classifications (with ALL categories) ---
    cls_raw = data.get("classificacoes") or []
    cls_rows = []
    for cls in cls_raw:
        cats_raw = cls.get("categorias") or []
        if cats_raw:
            categories = pd.DataFrame(
                [
                    {
                        "category_id": pluck_str(cat, "id"),
                        "category_name": pluck_str(cat, "nome"),
                        "category_unit": pluck_str(cat, "unidade"),
                        "category_level": pluck_str(cat, "nivel"),
                    }
                    for cat in cats_raw
                ]
            )
        else:
            categories = _empty_categories()
        cls_rows.append(
            {
                "id": pluck_str(cls, "id"),
                "name": pluck_str(cls, "nome"),
                "categories": categories,
            }
        )
    classifications = (
        pd.DataFrame(cls_rows)
        if cls_rows
        else pd.DataFrame(columns=["id", "name", "categories"])
    )

    # --- Territorial level ---
    nt_raw = data.get("nivelTerritorial") or {}
    territorial_level = {
        "administrative": list(nt_raw.get("Administrativo") or []),
        "special": list(nt_raw.get("Especial") or []),
        "ibge": list(nt_raw.get("IBGE") or []),
    }

    # --- Periodicity ---
    per_raw = data.get("periodicidade") or {}
    periodicity = {
        "frequency": per_raw.get("frequencia"),
        "start": per_raw.get("inicio"),
        "end": per_raw.get("fim"),
    }

    result = IbgeMetadata(
        id=data.get("id"),
        name=data.get("nome"),
        url=data.get("URL"),
        survey=data.get("pesquisa"),
        subject=data.get("assunto"),
        periodicity=periodicity,
        territorial_level=territorial_level,
        variables=variables,
        classifications=classifications,
    )

    _cache._AGG_META_CACHE[cache_key] = result
    _report(result, aggregate, cached_flag=False)
    return result


def _report(meta: IbgeMetadata, aggregate: int, cached_flag: bool) -> None:
    n_vars = len(meta.variables)
    n_cls = len(meta.classifications)
    n_cats = int(sum(len(c) for c in meta.classifications["categories"])) if n_cls else 0
    suffix = " (cached)" if cached_flag else ""
    _msg.success(
        f"Aggregate {aggregate}: {n_vars} variables, {n_cls} classifications, "
        f"{n_cats} categories{suffix}."
    )


def get_cached_metadata(aggregate: int) -> IbgeMetadata:
    """Internal: fetch metadata through the cache (mirrors the R helper)."""
    return ibge_metadata(aggregate)
