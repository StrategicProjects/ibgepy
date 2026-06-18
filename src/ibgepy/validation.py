"""Validate query parameters against an aggregate's metadata before calling.

Ported from the R package's ``validacao.R``. Invalid input raises
:class:`ValidationError` with a message listing the allowed values.
"""
from __future__ import annotations

import re
from typing import Any, List, Mapping, Optional

from .metadata import IbgeMetadata, get_cached_metadata


class ValidationError(ValueError):
    """Raised when a parameter does not match the aggregate metadata."""


def _all_levels(meta: IbgeMetadata) -> List[str]:
    tl = meta.territorial_level
    return [*tl["administrative"], *tl["special"], *tl["ibge"]]


def _as_list(x: Any) -> list:
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def extract_levels(localities: Any) -> List[str]:
    """Geographic level codes implied by a localities argument."""
    if localities is None:
        return []
    if isinstance(localities, str):
        if re.fullmatch(r"BR", localities, flags=re.IGNORECASE):
            return ["N1"]
        return list(dict.fromkeys(re.findall(r"N\d+", localities)))
    if isinstance(localities, (list, tuple)):
        found: List[str] = []
        for item in localities:
            found.extend(re.findall(r"N\d+", str(item)))
        return list(dict.fromkeys(found))
    if isinstance(localities, Mapping):
        return list(dict.fromkeys(localities.keys()))
    return []


def extract_numeric_periods(periods: Any) -> List[float]:
    """Positive numeric periods (negative = last-N and ranges are expanded)."""
    if periods is None:
        return []
    if isinstance(periods, int) and periods < 0:
        return []
    if isinstance(periods, (int, float)):
        return [float(periods)] if periods > 0 else []
    if isinstance(periods, (list, tuple)):
        out: List[float] = []
        for p in periods:
            out.extend(extract_numeric_periods(p))
        return out
    if isinstance(periods, str):
        text = periods.strip()
        if re.fullmatch(r"-\d+", text):
            return []
        out = []
        for part in text.split("|"):
            if "-" in part and not part.startswith("-"):
                bounds = part.split("-")
                if len(bounds) == 2:
                    try:
                        lo, hi = int(bounds[0]), int(bounds[1])
                        out.extend(float(v) for v in range(lo, hi + 1))
                        continue
                    except ValueError:
                        pass
            try:
                val = float(part)
                if val > 0:
                    out.append(val)
            except ValueError:
                pass
        return out
    return []


def validate_level(meta: IbgeMetadata, level: Any) -> None:
    valid = _all_levels(meta)
    if not valid:
        return
    requested = [str(x) for x in _as_list(level)] if level is not None else []
    invalid = [x for x in requested if x not in valid]
    if invalid:
        raise ValidationError(
            f"Geographic level(s) {invalid} not available for aggregate {meta.id}. "
            f"Available levels: {valid}."
        )


def validate_localities(meta: IbgeMetadata, localities: Any) -> None:
    valid = _all_levels(meta)
    if not valid:
        return
    requested = extract_levels(localities)
    if not requested:
        return
    invalid = [x for x in requested if x not in valid]
    if invalid:
        raise ValidationError(
            f"Geographic level(s) {invalid} not available for aggregate {meta.id}. "
            f"Available levels: {valid}."
        )


def validate_periods(meta: IbgeMetadata, periods: Any) -> None:
    nums = extract_numeric_periods(periods)
    if not nums:
        return
    try:
        start = float(meta.periodicity.get("start"))
        end = float(meta.periodicity.get("end"))
    except (TypeError, ValueError):
        return
    out_of_range = [n for n in nums if n < start or n > end]
    if out_of_range:
        freq = meta.periodicity.get("frequency") or "N/A"
        pretty = [int(n) for n in out_of_range]
        raise ValidationError(
            f"Period(s) {pretty} out of range for aggregate {meta.id}. "
            f"Valid range: {int(start)} to {int(end)} ({freq})."
        )


def validate_variables(meta: IbgeMetadata, variable: Any) -> None:
    if variable is None or variable in ("all", "todas", "allxp"):
        return
    valid = meta.variables
    if len(valid) == 0:
        return
    requested = [str(v) for v in _as_list(variable)]
    valid_ids = set(valid["id"].astype(str))
    invalid = [v for v in requested if v not in valid_ids]
    if invalid:
        listing = "\n".join(
            f"  {row.id} - {row.name} ({row.unit})" for row in valid.itertuples()
        )
        raise ValidationError(
            f"Variable(s) {invalid} not found in aggregate {meta.id}.\n"
            f"Available variables:\n{listing}"
        )


def validate_classifications(meta: IbgeMetadata, classification: Any) -> None:
    if classification is None or not isinstance(classification, Mapping):
        return
    valid_cls = meta.classifications
    if len(valid_cls) == 0:
        return
    valid_ids = list(valid_cls["id"].astype(str))
    for cls_id, cats_requested in classification.items():
        cls_id = str(cls_id)
        if cls_id not in valid_ids:
            listing = "\n".join(
                f"  {row.id} - {row.name}" for row in valid_cls.itertuples()
            )
            raise ValidationError(
                f"Classification {cls_id!r} not found in aggregate {meta.id}.\n"
                f"Available classifications:\n{listing}"
            )
        if cats_requested in ("all", "todos"):
            continue
        idx = valid_ids.index(cls_id)
        cats_valid = valid_cls.iloc[idx]["categories"]
        valid_cat_ids = set(cats_valid["category_id"].astype(str))
        cats_invalid = [str(c) for c in _as_list(cats_requested) if str(c) not in valid_cat_ids]
        if cats_invalid:
            cls_name = valid_cls.iloc[idx]["name"]
            n_total = len(cats_valid)
            preview = "\n".join(
                f"  {r.category_id} - {r.category_name}"
                for r in cats_valid.head(10).itertuples()
            )
            more = (
                f"\n  ... and {n_total - 10} more."
                if n_total > 10
                else ""
            )
            raise ValidationError(
                f"Category(ies) {cats_invalid} not found in classification "
                f"{cls_id!r} ({cls_name}).\n"
                f"First categories available ({n_total} total):\n{preview}{more}"
            )


def validate_query(
    meta: IbgeMetadata,
    localities: Any = None,
    periods: Any = None,
    variable: Any = None,
    classification: Optional[Mapping[str, Any]] = None,
    level: Any = None,
) -> None:
    """Validate every supplied parameter against the aggregate metadata."""
    if level is not None:
        validate_level(meta, level)
    if localities is not None:
        validate_localities(meta, localities)
    if periods is not None:
        validate_periods(meta, periods)
    if variable is not None:
        validate_variables(meta, variable)
    if classification is not None:
        validate_classifications(meta, classification)


__all__ = ["ValidationError", "validate_query", "get_cached_metadata"]
