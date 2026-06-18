"""Survey catalog and institutional metadata (IBGE Metadata API v2)."""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from . import _cache, _msg
from ._client import metadata_request
from ._format import pluck_str


# --- Cached helpers --------------------------------------------------------


def _get_survey_catalog() -> Dict[str, str]:
    cached = _cache._SURVEY_CACHE.get("catalog")
    if cached is not None:
        return cached
    data = metadata_request("pesquisas", label="survey catalog")
    catalog = {str(s.get("codigo") or ""): (s.get("nome") or "") for s in data}
    _cache._SURVEY_CACHE["catalog"] = catalog
    return catalog


def _get_survey_periods(survey: str) -> pd.DataFrame:
    key = f"periods_{survey}"
    cached = _cache._SURVEY_CACHE.get(key)
    if cached is not None:
        return cached
    data = metadata_request("pesquisas", survey, "periodos", label=f"periods for survey {survey}")
    rows = []
    for p in data:
        month_val = p.get("mes")
        if month_val in (None, "", "0"):
            month = pd.NA
        else:
            try:
                month = int(month_val)
            except (TypeError, ValueError):
                month = pd.NA
        rows.append(
            {
                "year": int(pluck_str(p, "ano")),
                "month": month,
                "order": int(pluck_str(p, "ordem")),
            }
        )
    result = pd.DataFrame(rows, columns=["year", "month", "order"]).astype(
        {"year": "Int64", "month": "Int64", "order": "Int64"}
    )
    _cache._SURVEY_CACHE[key] = result
    return result


# --- Validators ------------------------------------------------------------


def _validate_survey_code(survey: str) -> None:
    if not isinstance(survey, str) or not survey:
        raise ValueError(
            "`survey` must be a single non-empty string. "
            "Use ibge_surveys() to see available survey codes."
        )
    catalog = _get_survey_catalog()
    if survey in catalog:
        return
    closest = difflib.get_close_matches(survey.upper(), [c.upper() for c in catalog], n=5, cutoff=0)
    upper_map = {c.upper(): c for c in catalog}
    suggestions = "\n".join(
        f"  * {upper_map[c]} - {catalog[upper_map[c]]}" for c in closest
    )
    raise ValueError(
        f"Survey code {survey!r} not found in the IBGE catalog.\n"
        f"Did you mean one of these?\n{suggestions}\n"
        f"Use ibge_surveys() to see all {len(catalog)} valid codes."
    )


def _validate_survey_period(survey: str, year: int, month: Optional[int]) -> None:
    periods = _get_survey_periods(survey)
    if len(periods) == 0:
        raise ValueError(
            f"No metadata periods found for survey {survey!r}. "
            "This survey may not have period-specific metadata."
        )
    available_years = sorted(int(y) for y in periods["year"].dropna().unique())
    if int(year) not in available_years:
        raise ValueError(
            f"Year {year} not available for survey {survey!r}. "
            f"Available years: {available_years[0]} to {available_years[-1]} "
            f"({len(available_years)} total). "
            f'Use ibge_survey_periods("{survey}") to see all periods.'
        )
    year_rows = periods[periods["year"] == int(year)]
    available_months = sorted(int(m) for m in year_rows["month"].dropna().unique())
    if month is not None:
        if not available_months:
            raise ValueError(
                f"Survey {survey!r} does not use monthly periods (it is "
                f"structural/annual). Remove the `month` argument."
            )
        if int(month) not in available_months:
            raise ValueError(
                f"Month {month} not available for survey {survey!r} in {year}. "
                f"Available months for {year}: {available_months}. "
                f'Use ibge_survey_periods("{survey}") to see all periods.'
            )
    elif available_months:
        _msg.warn(
            f"Survey {survey!r} has monthly periods for {year}. "
            f"Available months: {available_months}. "
            "Consider specifying `month` for more precise results."
        )


# --- Public functions ------------------------------------------------------


def ibge_surveys(thematic_classifications: bool = True) -> pd.DataFrame:
    """List the full catalog of IBGE surveys with institutional metadata.

    Uses the Metadata API (v2). If ``thematic_classifications`` is ``True``
    (default), a ``thematic_classifications`` column holds, per row, a nested
    DataFrame of classification details.
    """
    data = metadata_request("pesquisas", label="survey catalog")
    rows = []
    for s in data:
        row = {
            "id": pluck_str(s, "codigo"),
            "name": pluck_str(s, "nome"),
            "name_en": pluck_str(s, "nome_ingles"),
            "status": pluck_str(s, "situacao"),
            "category": pluck_str(s, "categoria"),
            "collection_frequency": pluck_str(s, "periodicidade_coleta"),
            "publication_frequency": pluck_str(s, "periodicidade_divulgacao"),
        }
        if thematic_classifications:
            cls_raw = s.get("classificacoes_tematicas") or []
            row["thematic_classifications"] = pd.DataFrame(
                [
                    {
                        "name": pluck_str(cls, "nome"),
                        "name_en": pluck_str(cls, "nome_ingles"),
                        "domain": pluck_str(cls, "dominio"),
                        "domain_en": pluck_str(cls, "dominio_ingles"),
                        "description": pluck_str(cls, "descricao"),
                    }
                    for cls in cls_raw
                ],
                columns=["name", "name_en", "domain", "domain_en", "description"],
            )
        rows.append(row)

    result = pd.DataFrame(rows)
    _msg.success(f"{len(result)} survey(s) found.")
    return result


def ibge_survey_periods(survey: str) -> pd.DataFrame:
    """List the periods (year/month) for which a survey has metadata.

    The survey code is validated against the IBGE catalog first; invalid
    codes raise a helpful error with suggestions. Returns a DataFrame with
    columns ``year``, ``month`` (``<NA>`` for structural surveys), ``order``.
    """
    _validate_survey_code(survey)
    result = _get_survey_periods(survey)
    _msg.success(f"{len(result)} period(s) found for survey {survey!r}.")
    return result


@dataclass
class IbgeSurveyMetadata:
    """Institutional/methodological metadata for a survey in a period."""

    status: Any
    category: Any
    type: Any
    area: Any
    acronym: Any
    start_date: Any
    deactivation_date: Any
    sidra_url: Any
    concla_url: Any
    thematic_classifications: pd.DataFrame
    occurrences: List[Any]

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"<IbgeSurveyMetadata {self.acronym!r} | status={self.status!r}, "
            f"category={self.category!r}, {len(self.occurrences)} occurrence(s)>"
        )


def ibge_survey_metadata(
    survey: str,
    year: int,
    month: Optional[int] = None,
    order: int = 0,
) -> IbgeSurveyMetadata:
    """Detailed metadata for a survey in a given reference period.

    Both the survey code and the year/month combination are validated against
    the IBGE catalog before the request is sent.
    """
    if not isinstance(year, int):
        raise ValueError("`year` must be a single integer.")
    if month is not None and (not isinstance(month, int) or month < 1 or month > 12):
        raise ValueError("`month` must be an integer between 1 and 12.")

    _validate_survey_code(survey)
    _validate_survey_period(survey, year, month)

    path: List[Any] = [survey, int(year)]
    label = f"metadata for {survey} ({year}"
    if month is not None:
        path.append(int(month))
        label += f"/{month}"
    path.append(int(order))
    label += ")"

    data = metadata_request(*path, label=label)
    if isinstance(data, list) and len(data) >= 1:
        data = data[0]

    cls_raw = data.get("classificacoes_tematicas") or []
    thematic = pd.DataFrame(
        [{k: (None if v is None else str(v)) for k, v in cls.items()} for cls in cls_raw]
    )

    occurrences = data.get("ocorrencias_pesquisa") or []

    result = IbgeSurveyMetadata(
        status=data.get("situacao"),
        category=data.get("categoria"),
        type=data.get("tipo"),
        area=data.get("area"),
        acronym=data.get("sigla"),
        start_date=data.get("data_inicio"),
        deactivation_date=data.get("data_desativacao"),
        sidra_url=data.get("url-sidra"),
        concla_url=data.get("url-concla"),
        thematic_classifications=thematic,
        occurrences=occurrences,
    )
    _msg.success(f"Survey {survey!r} ({year}): {len(occurrences)} metadata occurrence(s).")
    return result
