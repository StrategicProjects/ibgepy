"""Translate and execute SIDRA API URLs as ibgepy calls."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import pandas as pd

from . import _msg
from .validation import _all_levels, get_cached_metadata

_LEVEL_NAMES = {
    "N1": "Brazil",
    "N2": "Major region",
    "N3": "State (UF)",
    "N6": "Municipality",
    "N7": "Metropolitan area",
    "N8": "Mesoregion",
    "N9": "Microregion",
    "N10": "District",
    "N11": "Sub-district",
    "N13": "Legal Amazon",
    "N14": "Semiarid",
    "N15": "Immediate geographic region",
    "N17": "Intermediate geographic region",
}


@dataclass
class SidraQuery:
    """Parsed SIDRA query, enriched with names from the aggregate metadata."""

    aggregate: Dict[str, Any]
    variables: pd.DataFrame
    periods: str
    localities: List[Dict[str, Any]]
    classifications: List[Dict[str, Any]]
    ibger_call: str
    periodicity: Dict[str, Any]

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"<SidraQuery aggregate={self.aggregate.get('id')} "
            f"({self.aggregate.get('name')!r}) | {len(self.variables)} variable(s)>"
        )


def parse_sidra_url(url: str) -> SidraQuery:
    """Convert a SIDRA API URL into a structured, name-enriched breakdown."""
    url = unquote(url)
    path = re.sub(r".*?/values/", "", url, flags=re.IGNORECASE)
    path = re.sub(r"\?.*", "", path)
    path = re.sub(r"/$", "", path)
    segments = path.split("/")

    aggregate_id: Optional[str] = None
    variables: List[str] = []
    periods = ""
    localities: List[Dict[str, str]] = []
    classifications: Dict[str, List[str]] = {}

    i = 0
    n = len(segments)
    while i < n:
        seg = segments[i]
        if seg == "t" and i + 1 < n:
            aggregate_id = segments[i + 1]
            i += 2
        elif re.fullmatch(r"n\d+", seg) and i + 1 < n:
            level = "N" + seg[1:]
            localities.append({"level": level, "codes": segments[i + 1]})
            i += 2
        elif seg == "v" and i + 1 < n:
            variables = segments[i + 1].split(",")
            i += 2
        elif seg == "p" and i + 1 < n:
            periods = segments[i + 1]
            i += 2
        elif re.fullmatch(r"c\d+", seg) and i + 1 < n:
            cls_id = seg[1:]
            classifications[cls_id] = segments[i + 1].split(",")
            i += 2
        else:
            i += 1

    if aggregate_id is None:
        raise ValueError(
            "Could not find an aggregate ID in the URL. "
            "Expected a SIDRA API URL with /t/{id} in the path."
        )

    meta = get_cached_metadata(int(aggregate_id))

    # --- Resolve variable names ---
    if variables and variables != ["allxp"]:
        meta_vars = meta.variables.set_index(meta.variables["id"].astype(str))
        var_rows = []
        for vid in variables:
            if vid in meta_vars.index:
                row = meta_vars.loc[vid]
                var_rows.append({"id": vid, "name": row["name"], "unit": row["unit"]})
            else:
                var_rows.append({"id": vid, "name": None, "unit": None})
        var_info = pd.DataFrame(var_rows, columns=["id", "name", "unit"])
    else:
        var_info = meta.variables.copy()

    # --- Resolve classification/category names ---
    cls_info = []
    for cls_id, cats in classifications.items():
        cls_match = meta.classifications[meta.classifications["id"].astype(str) == cls_id]
        cls_name = cls_match.iloc[0]["name"] if len(cls_match) else None
        if cats == ["all"]:
            cat_detail = pd.DataFrame(
                [{"category_id": "all", "category_name": "(all categories)"}]
            )
        elif len(cls_match):
            all_cats = cls_match.iloc[0]["categories"]
            lookup = all_cats.set_index(all_cats["category_id"].astype(str))
            cat_rows = []
            for cid in cats:
                if cid in lookup.index:
                    cat_rows.append(
                        {"category_id": cid, "category_name": lookup.loc[cid]["category_name"]}
                    )
                else:
                    cat_rows.append({"category_id": cid, "category_name": None})
            cat_detail = pd.DataFrame(cat_rows, columns=["category_id", "category_name"])
        else:
            cat_detail = pd.DataFrame(
                [{"category_id": c, "category_name": None} for c in cats]
            )
        cls_info.append({"id": cls_id, "name": cls_name, "categories": cat_detail})

    # --- Resolve locality level names ---
    loc_info = []
    for loc in localities:
        loc_info.append(
            {
                "level": loc["level"],
                "level_name": _LEVEL_NAMES.get(loc["level"], "unknown level"),
                "codes": loc["codes"],
            }
        )
    _warn_sidra_levels(meta, loc_info)

    ibger_call = _build_ibgepy_call(
        aggregate_id, list(var_info["id"]), periods, localities, classifications
    )

    return SidraQuery(
        aggregate={"id": aggregate_id, "name": meta.name},
        variables=var_info,
        periods=periods,
        localities=loc_info,
        classifications=cls_info,
        ibger_call=ibger_call,
        periodicity=meta.periodicity,
    )


def _warn_sidra_levels(meta, localities) -> None:
    """Warn about territorial levels the aggregate does not offer.

    The SIDRA API rejects such URLs; here the parse still succeeds so the
    query can be inspected, and :func:`fetch_sidra_url` fails through the
    regular validation.
    """
    valid = _all_levels(meta)
    if not valid or not localities:
        return
    invalid = [loc["level"] for loc in localities if loc["level"] not in valid]
    if invalid:
        _msg.warn(
            f"Geographic level(s) {invalid} not available for aggregate {meta.id}. "
            f"Available levels: {valid}. fetch_sidra_url() will fail for this URL."
        )


def _localities_arg(localities: List[Dict[str, str]]) -> Any:
    """Translate parsed localities into an ``ibge_variables()`` argument.

    Shared by the printed "equivalent call" and :func:`fetch_sidra_url`, so
    the two always agree: ``"BR"`` / a level code for a single level, a dict
    when every level has specific codes, and the API's pipe syntax
    (``"N1|N3[33,35]"``) when several levels are mixed with ``all``.
    """
    if not localities:
        return "BR"
    if len(localities) == 1:
        loc = localities[0]
        codes = loc["codes"].lower()
        if codes == "all" and loc["level"] == "N1":
            return "BR"
        if codes == "all":
            return loc["level"]
        return {loc["level"]: [int(x) for x in loc["codes"].split(",")]}

    if any(loc["codes"].lower() == "all" for loc in localities):
        parts = [
            loc["level"] if loc["codes"].lower() == "all" else f"{loc['level']}[{loc['codes']}]"
            for loc in localities
        ]
        return "|".join(parts)
    return {loc["level"]: [int(x) for x in loc["codes"].split(",")] for loc in localities}


def _build_ibgepy_call(aggregate_id, var_ids, periods, localities, classifications) -> str:
    parts = f"ibge_variables(\n    aggregate={aggregate_id}"

    if var_ids and var_ids != ["allxp"]:
        if len(var_ids) == 1:
            parts += f",\n    variable={var_ids[0]}"
        else:
            parts += f",\n    variable=[{', '.join(str(v) for v in var_ids)}]"

    if periods:
        m = re.match(r"^last\s+", periods, flags=re.IGNORECASE)
        if m:
            n = re.sub(r"^last\s+", "", periods, flags=re.IGNORECASE)
            parts += f",\n    periods=-{n}"
        else:
            parts += f',\n    periods="{periods}"'

    if localities:
        arg = _localities_arg(localities)
        if isinstance(arg, str):
            parts += f',\n    localities="{arg}"'
        else:
            dict_parts = ", ".join(
                f'"{level}": {ids[0] if len(ids) == 1 else ids}' for level, ids in arg.items()
            )
            parts += f",\n    localities={{{dict_parts}}}"

    if classifications:
        cls_parts = []
        for cls_id, cats in classifications.items():
            if cats == ["all"]:
                cls_parts.append(f'"{cls_id}": "all"')
            elif len(cats) == 1:
                cls_parts.append(f'"{cls_id}": {cats[0]}')
            else:
                cls_parts.append(f'"{cls_id}": [{", ".join(cats)}]')
        parts += f",\n    classification={{{', '.join(cls_parts)}}}"

    return parts + "\n)"


def fetch_sidra_url(url: str, validate: bool = True) -> pd.DataFrame:
    """Parse a SIDRA API URL and fetch the data via :func:`ibge_variables`."""
    from .variables import ibge_variables

    parsed = parse_sidra_url(url)

    # --- Build localities argument ---
    localities: Any = _localities_arg(parsed.localities)

    # --- Build classification argument ---
    classification: Optional[Dict[str, Any]] = None
    if parsed.classifications:
        classification = {}
        for cls in parsed.classifications:
            cats = list(cls["categories"]["category_id"])
            classification[str(cls["id"])] = (
                "all" if cats == ["all"] else [int(c) for c in cats]
            )

    # --- Build variable argument ---
    variable: Any = None
    if len(parsed.variables) > 0:
        ids = list(parsed.variables["id"])
        if ids not in (["allxp"], ["all"]):
            variable = [int(v) for v in ids]

    # --- Build periods argument ---
    if parsed.periods:
        m = re.match(r"^last\s+", parsed.periods, flags=re.IGNORECASE)
        if m:
            periods: Any = -int(re.sub(r"^last\s+", "", parsed.periods, flags=re.IGNORECASE))
        else:
            periods = parsed.periods
    else:
        periods = -6

    return ibge_variables(
        aggregate=int(parsed.aggregate["id"]),
        variable=variable,
        periods=periods,
        localities=localities,
        classification=classification,
        validate=validate,
    )
