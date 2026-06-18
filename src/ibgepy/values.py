"""Convert IBGE value columns to numeric, honoring special-value codes."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

#: IBGE tabular special codes (see IBGE presentation standards).
SPECIAL_NA = ("..", "...", "X")


def parse_ibge_value(x: Any) -> Any:
    """Coerce an IBGE ``value`` column to numeric.

    Conversions, following IBGE's tabular presentation standards:

    * ``"-"`` (numeric zero, not rounding) -> ``0``
    * ``".."`` (not applicable), ``"..."`` (not available), ``"X"``
      (suppressed) -> ``NaN``
    * everything else -> :func:`pandas.to_numeric`

    Accepts a scalar, a list, or a :class:`pandas.Series` and returns the
    matching shape (Series in, Series out; scalar in, float out).
    """
    scalar_input = not isinstance(x, (pd.Series, list, tuple, np.ndarray))
    series = pd.Series([x] if scalar_input else x)

    if pd.api.types.is_numeric_dtype(series):
        result = series.astype(float)
    else:
        text = series.astype("string")
        result = pd.to_numeric(text, errors="coerce")
        result = result.mask((text == "-").fillna(False), 0.0)
        result = result.mask(text.isin(SPECIAL_NA).fillna(False), np.nan)
        # Normalize to plain float64 (np.nan) rather than nullable Float64 (pd.NA).
        result = result.astype("float64")

    if scalar_input:
        value = result.iloc[0]
        return float(value) if pd.notna(value) else np.nan
    return result.reset_index(drop=True)
