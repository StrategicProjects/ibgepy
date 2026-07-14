"""ibgepy — access the IBGE Aggregate Data API (SIDRA) from Python.

A pandas-friendly port of the R package `ibger`. Query aggregates,
variables, localities, periods, subjects, surveys and metadata from the
surveys and censuses conducted by IBGE (Brazilian Institute of Geography and
Statistics).

Quick start
-----------
>>> import ibgepy
>>> ibgepy.ibge_variables(7060, localities="BR")          # doctest: +SKIP
>>> ibgepy.ibge_metadata(7060)                            # doctest: +SKIP
>>> ibgepy.ibge_subjects("internet")                      # doctest: +SKIP
"""
from __future__ import annotations

from ._cache import clear_cache as ibge_clear_cache
from ._client import IbgeError
from ._msg import set_verbose
from .aggregates import ibge_aggregates
from .localities import ibge_localities
from .metadata import IbgeMetadata, ibge_metadata
from .periods import ibge_periods
from .sidra_url import SidraQuery, fetch_sidra_url, parse_sidra_url
from .subjects import ibge_subjects
from .surveys import (
    IbgeSurveyMetadata,
    ibge_survey_metadata,
    ibge_survey_periods,
    ibge_surveys,
)
from .validation import ValidationError
from .values import parse_ibge_value
from .variables import ibge_variables

__version__ = "0.2.1"

__all__ = [
    "ibge_aggregates",
    "ibge_variables",
    "ibge_metadata",
    "ibge_periods",
    "ibge_localities",
    "ibge_subjects",
    "ibge_surveys",
    "ibge_survey_periods",
    "ibge_survey_metadata",
    "parse_ibge_value",
    "parse_sidra_url",
    "fetch_sidra_url",
    "ibge_clear_cache",
    "set_verbose",
    "IbgeMetadata",
    "IbgeSurveyMetadata",
    "SidraQuery",
    "IbgeError",
    "ValidationError",
    "__version__",
]
