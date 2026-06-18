from ibgepy.validation import extract_levels, extract_numeric_periods


def test_extract_levels():
    assert extract_levels("BR") == ["N1"]
    assert extract_levels("br") == ["N1"]
    assert extract_levels("N3") == ["N3"]
    assert extract_levels("N3|N6") == ["N3", "N6"]
    assert extract_levels(["N6", "N7"]) == ["N6", "N7"]
    assert extract_levels({"N6": [1, 2], "N3": 3}) == ["N6", "N3"]
    assert extract_levels(None) == []


def test_extract_numeric_periods():
    assert extract_numeric_periods(-6) == []
    assert extract_numeric_periods(None) == []
    assert extract_numeric_periods([201701, 201702]) == [201701.0, 201702.0]
    assert extract_numeric_periods("-3") == []
    assert extract_numeric_periods("201701|201702") == [201701.0, 201702.0]
    assert extract_numeric_periods("2017-2019") == [2017.0, 2018.0, 2019.0]
