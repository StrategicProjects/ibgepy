import math

import numpy as np
import pandas as pd

from ibgepy import parse_ibge_value


def test_parse_series_special_codes():
    out = parse_ibge_value(pd.Series(["1.5", "10", "-", "..", "...", "X", None]))
    expected = [1.5, 10.0, 0.0, np.nan, np.nan, np.nan, np.nan]
    assert len(out) == len(expected)
    for got, exp in zip(out.tolist(), expected):
        if math.isnan(exp):
            assert math.isnan(got)
        else:
            assert got == exp


def test_parse_list_input():
    out = parse_ibge_value(["-", "2"])
    assert out.tolist() == [0.0, 2.0]


def test_parse_numeric_passthrough():
    out = parse_ibge_value(pd.Series([1, 2, 3]))
    assert out.tolist() == [1.0, 2.0, 3.0]


def test_parse_scalar():
    assert parse_ibge_value("-") == 0.0
    assert parse_ibge_value("3.14") == 3.14
    assert math.isnan(parse_ibge_value(".."))
