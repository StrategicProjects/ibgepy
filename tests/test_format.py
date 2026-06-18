import pytest

from ibgepy._format import (
    format_classification,
    format_localities,
    format_periods,
    format_variable,
    pluck,
    pluck_str,
)


def test_format_localities_string_and_list_and_mapping():
    assert format_localities("BR") == "BR"
    assert format_localities("N3") == "N3"
    assert format_localities(["N3", "N6"]) == "N3|N6"
    assert format_localities({"N6": [3550308, 3304557]}) == "N6[3550308,3304557]"
    assert format_localities({"N3": [33, 35], "N6": 5208707}) == "N3[33,35]|N6[5208707]"


def test_format_localities_invalid():
    with pytest.raises(ValueError):
        format_localities(123)


def test_format_periods():
    assert format_periods(None) == "-6"
    assert format_periods(-6) == "-6"
    assert format_periods([201701, 201702]) == "201701|201702"
    assert format_periods("201701-201712") == "201701-201712"
    assert format_periods(202001) == "202001"


def test_format_variable():
    assert format_variable(None) == "allxp"
    assert format_variable("all") == "all"
    assert format_variable("todas") == "all"
    assert format_variable([284, 285]) == "284|285"
    assert format_variable(214) == "214"


def test_format_classification():
    assert format_classification(None) is None
    assert format_classification({"226": [4844, 96608], "218": 4780}) == "226[4844,96608]|218[4780]"
    assert format_classification({"226": "all"}) == "226[all]"
    with pytest.raises(ValueError):
        format_classification(["not", "a", "mapping"])


def test_pluck():
    obj = {"a": {"b": [10, 20]}}
    assert pluck(obj, "a", "b", 1) == 20
    assert pluck(obj, "a", "x", default="z") == "z"
    assert pluck(obj, "missing") is None
    assert pluck_str({"id": 5}, "id") == "5"
    assert pluck_str({}, "id", default="NA") == "NA"
