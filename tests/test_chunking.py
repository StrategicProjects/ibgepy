import pandas as pd
import pytest

from ibgepy._cache import _AGG_META_CACHE
from ibgepy._chunking import (
    IBGE_VALUE_LIMIT,
    build_chunk_plan,
    estimate_n_categories,
    estimate_n_periods,
    estimate_n_variables,
    resolve_chunk_limit,
    resolve_localities_for_chunking,
    resolve_period_ids,
    split_in_groups,
    units_to_localities_str,
)
from ibgepy.metadata import IbgeMetadata


def fake_meta(n_vars=8, cats_226=34):
    return IbgeMetadata(
        id=9999,
        name="fake",
        url=None,
        survey=None,
        subject=None,
        periodicity={},
        territorial_level={},
        variables=pd.DataFrame(
            {
                "id": [str(i) for i in range(1, n_vars + 1)],
                "name": [f"var {i}" for i in range(1, n_vars + 1)],
                "unit": ["un"] * n_vars,
            }
        ),
        classifications=pd.DataFrame(
            {
                "id": ["226"],
                "name": ["Produtos"],
                "categories": [
                    pd.DataFrame(
                        {
                            "category_id": [str(i) for i in range(1, cats_226 + 1)],
                            "category_name": [f"cat {i}" for i in range(1, cats_226 + 1)],
                        }
                    )
                ],
            }
        ),
    )


@pytest.fixture(autouse=True)
def _clean_cache():
    yield
    for key in [k for k in _AGG_META_CACHE if "9999" in k]:
        del _AGG_META_CACHE[key]


def test_resolve_chunk_limit():
    assert resolve_chunk_limit(True) == IBGE_VALUE_LIMIT == 50000
    assert resolve_chunk_limit(False) is None
    assert resolve_chunk_limit(5000) == 5000
    with pytest.raises(ValueError):
        resolve_chunk_limit("yes")
    with pytest.raises(ValueError):
        resolve_chunk_limit(-1)


def test_split_in_groups():
    groups = split_in_groups(list(range(1, 11)), 3)
    assert len(groups) == 4
    assert groups[0] == [1, 2, 3]
    assert groups[3] == [10]
    assert [x for g in groups for x in g] == list(range(1, 11))
    assert split_in_groups([1, 2, 3], 10) == [[1, 2, 3]]


def test_units_to_localities_str():
    units = [("N3", "33"), ("N3", "35"), ("N6", "3550308")]
    assert units_to_localities_str(units) == "N3[33,35]|N6[3550308]"


def test_estimate_n_periods():
    assert estimate_n_periods(None) == 6
    assert estimate_n_periods(-4) == 4
    assert estimate_n_periods("-4") == 4
    assert estimate_n_periods([2020, 2021]) == 2
    assert estimate_n_periods("201701-201712") == 12


def test_estimate_n_variables():
    get_meta = lambda: fake_meta(n_vars=8)  # noqa: E731
    assert estimate_n_variables(get_meta, None) == 8
    assert estimate_n_variables(get_meta, "all") == 16
    assert estimate_n_variables(get_meta, [214, 215, 216]) == 3

    def no_meta():
        raise AssertionError("metadata should not be fetched")

    assert estimate_n_variables(no_meta, [214, 215]) == 2


def test_estimate_n_categories():
    get_meta = lambda: fake_meta(cats_226=34)  # noqa: E731
    assert estimate_n_categories(get_meta, None) == 1
    assert estimate_n_categories(get_meta, {"226": [1, 2, 3]}) == 3
    assert estimate_n_categories(get_meta, {"226": "all"}) == 34
    assert estimate_n_categories(get_meta, {"226": [1, 2], "218": [1, 2, 3]}) == 6


def test_resolve_localities_without_api():
    res = resolve_localities_for_chunking(9999, "BR")
    assert res["n"] == 1
    assert res["units"] is None

    res = resolve_localities_for_chunking(9999, {"N3": [33, 35], "N6": 3550308})
    assert res["n"] == 3
    assert res["units"] == [("N3", "33"), ("N3", "35"), ("N6", "3550308")]


def test_resolve_localities_uses_cached_level_ids():
    _AGG_META_CACHE["locality_ids_9999_N3"] = [str(i) for i in range(1, 28)]
    res = resolve_localities_for_chunking(9999, "N3")
    assert res["n"] == 27
    assert res["units"][0] == ("N3", "1")


def test_build_chunk_plan_small_query_returns_none():
    plan = build_chunk_plan(
        9999,
        None,
        variable=[214],
        periods=[2020, 2021],
        localities={"N3": "33"},
        classification=None,
        limit=100000,
    )
    assert plan is None


def test_build_chunk_plan_splits_by_periods_first():
    _AGG_META_CACHE["period_ids_9999"] = [str(y) for y in range(2000, 2020)]
    # 2 variables x 25 localities = 50 values per period; limit 300 ->
    # 6 periods per chunk -> 4 chunks for 20 periods.
    plan = build_chunk_plan(
        9999,
        None,
        variable=[1, 2],
        periods=-20,
        localities={"N3": [str(i) for i in range(1, 26)]},
        classification=None,
        limit=300,
    )
    assert len(plan) == 4
    assert plan[0]["periods_str"] == "|".join(str(y) for y in range(2000, 2006))
    assert plan[3]["periods_str"] == "2018|2019"
    expected_locs = "N3[" + ",".join(str(i) for i in range(1, 26)) + "]"
    assert plan[0]["localities_str"] == expected_locs


def test_build_chunk_plan_splits_localities_when_period_too_large():
    _AGG_META_CACHE["period_ids_9999"] = [str(y) for y in range(2000, 2020)]
    # 2 variables x 25 localities = 50 values per period; limit 40 -> split
    # localities in groups of 20 -> 2 groups x 20 periods = 40 chunks.
    plan = build_chunk_plan(
        9999,
        None,
        variable=[1, 2],
        periods=-20,
        localities={"N3": [str(i) for i in range(1, 26)]},
        classification=None,
        limit=40,
    )
    assert len(plan) == 40
    assert plan[0]["periods_str"] == "2000"
    assert plan[0]["localities_str"] == "N3[" + ",".join(str(i) for i in range(1, 21)) + "]"
    assert plan[1]["periods_str"] == "2000"
    assert plan[1]["localities_str"] == "N3[21,22,23,24,25]"


def test_resolve_period_ids():
    _AGG_META_CACHE["period_ids_9999"] = [str(y) for y in range(2000, 2020)]
    assert resolve_period_ids(9999, -3) == ["2017", "2018", "2019"]
    assert resolve_period_ids(9999, [2005, 2007]) == ["2005", "2007"]
    assert resolve_period_ids(9999, "2005-2007") == ["2005", "2006", "2007"]
