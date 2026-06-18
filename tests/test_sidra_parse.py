import pandas as pd
import pytest

import ibgepy.metadata as metadata_mod
from ibgepy.metadata import IbgeMetadata
from ibgepy.sidra_url import parse_sidra_url


@pytest.fixture
def fake_metadata(monkeypatch):
    categories = pd.DataFrame(
        [
            {"category_id": "7169", "category_name": "Geral", "category_unit": None, "category_level": None},
        ]
    )
    meta = IbgeMetadata(
        id=7060,
        name="IPCA",
        url=None,
        survey="PMC",
        subject="Índices de preços",
        periodicity={"frequency": "mensal", "start": "201201", "end": "202401"},
        territorial_level={"administrative": ["N1"], "special": [], "ibge": []},
        variables=pd.DataFrame([{"id": "63", "name": "IPCA var.", "unit": "%"}]),
        classifications=pd.DataFrame(
            [{"id": "315", "name": "Geral, grupo...", "categories": categories}]
        ),
    )
    monkeypatch.setattr(metadata_mod, "ibge_metadata", lambda aggregate: meta)
    # validation imports get_cached_metadata -> ibge_metadata; patch there too
    import ibgepy.validation as v
    monkeypatch.setattr(v, "get_cached_metadata", lambda aggregate: meta)
    return meta


def test_parse_sidra_url_structure(fake_metadata):
    url = "https://apisidra.ibge.gov.br/values/t/7060/n1/all/v/63/p/last%2012/c315/7169"
    q = parse_sidra_url(url)
    assert q.aggregate == {"id": "7060", "name": "IPCA"}
    assert list(q.variables["id"]) == ["63"]
    assert q.periods == "last 12"
    assert q.localities[0]["level"] == "N1"
    assert q.localities[0]["level_name"] == "Brazil"
    assert q.classifications[0]["id"] == "315"
    assert list(q.classifications[0]["categories"]["category_id"]) == ["7169"]
    # Equivalent call is rendered with last-N translated to a negative period
    assert "aggregate=7060" in q.ibger_call
    assert "variable=63" in q.ibger_call
    assert "periods=-12" in q.ibger_call


def test_parse_sidra_url_requires_aggregate(fake_metadata):
    with pytest.raises(ValueError):
        parse_sidra_url("https://apisidra.ibge.gov.br/values/n1/all/v/63")
