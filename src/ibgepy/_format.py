"""Helpers that turn Python arguments into IBGE API query/path fragments.

Ported from the R package's ``utils.R`` (``format_*`` helpers and ``pluck``).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Union

Localities = Union[str, Sequence[str], Mapping[str, Any]]
Classification = Optional[Mapping[str, Any]]


def pluck(obj: Any, *keys: Any, default: Any = None) -> Any:
    """Safely walk nested dicts/lists, returning ``default`` on any miss."""
    cur = obj
    for key in keys:
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            return default
    return cur if cur is not None else default


def pluck_str(obj: Any, *keys: Any, default: Optional[str] = None) -> Optional[str]:
    val = pluck(obj, *keys, default=None)
    if val is None:
        return default
    return str(val)


def _seq(x: Any) -> list:
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def format_classification(classification: Classification) -> Optional[str]:
    """Named mapping -> ``226[4844,96608]|218[4780]`` (or ``226[all]``)."""
    if classification is None:
        return None
    if not isinstance(classification, Mapping):
        raise ValueError(
            "`classification` must be a mapping. "
            'Example: {"226": [4844, 96608], "218": 4780}'
        )
    parts = []
    for cls, cats in classification.items():
        if cats in ("all", "todos"):
            parts.append(f"{cls}[all]")
        else:
            joined = ",".join(str(c) for c in _seq(cats))
            parts.append(f"{cls}[{joined}]")
    return "|".join(parts)


def format_localities(localities: Localities) -> str:
    """Accepts ``"BR"``, a level code, a list of codes, or a named mapping."""
    if isinstance(localities, str):
        return localities
    if isinstance(localities, Mapping):
        parts = []
        for level, ids in localities.items():
            joined = ",".join(str(i) for i in _seq(ids))
            parts.append(f"{level}[{joined}]")
        return "|".join(parts)
    if isinstance(localities, (list, tuple)):
        return "|".join(str(x) for x in localities)
    raise ValueError(
        "`localities` must be 'BR', a level code (e.g. 'N3'), a list, "
        'or a mapping like {"N6": [3550308, 3304557]}.'
    )


def format_periods(periods: Any) -> str:
    """Negative int -> last-N; otherwise join values with ``|``. ``None`` -> -6."""
    if periods is None:
        return "-6"
    if isinstance(periods, int) and periods < 0:
        return str(periods)
    if isinstance(periods, (list, tuple)):
        return "|".join(str(p) for p in periods)
    return str(periods)


def format_variable(variable: Any) -> str:
    """``None`` -> ``allxp``; ``"all"`` -> ``all``; else join with ``|``."""
    if variable is None:
        return "allxp"
    if variable in ("all", "todas"):
        return "all"
    return "|".join(str(v) for v in _seq(variable))
