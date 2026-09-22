import pandas as pd
import pytest

import ibgepy.aggregates as agg_mod
from ibgepy.aggregates import ibge_aggregates


@pytest.mark.parametrize(
    "kwargs",
    [
        {"classification": "AAA"},
        {"subject": "abate"},
        {"periodicity": 15},
        {"periodicity": 30},
        {"periodicity": "monthly"},
        {"level": "state"},
        {"level": 3},
        {"period": "202001"},
        {"period": "P5[2020-01]"},
    ],
)
def test_ibge_aggregates_rejects_malformed_filters(kwargs):
    with pytest.raises(ValueError):
        ibge_aggregates(**kwargs)


def test_ibge_aggregates_empty_result_warns(monkeypatch, capsys):
    monkeypatch.setattr(agg_mod, "ibge_request", lambda **kwargs: [])
    result = ibge_aggregates(periodicity="P59")
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["survey_id", "survey_name", "aggregate_id", "aggregate_name"]
    assert len(result) == 0
    assert "No aggregates found" in capsys.readouterr().err
