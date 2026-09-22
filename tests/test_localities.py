import pandas as pd

import ibgepy.localities as loc_mod
from ibgepy.localities import ibge_localities


def test_ibge_localities_queries_each_level_and_keeps_columns(monkeypatch, capsys):
    calls = []

    def fake_request(*path, label=""):
        calls.append(path[-1])
        if path[-1] == "N7":
            return []
        return [{"id": "1", "nome": "Brasil", "nivel": {"id": path[-1], "nome": "x"}}]

    monkeypatch.setattr(loc_mod, "ibge_request", fake_request)
    result = ibge_localities(1437, level=["N6", "N7"], validate=False)
    assert calls == ["N6", "N7"]
    assert list(result["level_id"]) == ["N6"]

    monkeypatch.setattr(loc_mod, "ibge_request", lambda *path, label="": [])
    empty = ibge_localities(1437, level=["N6", "N7"], validate=False)
    assert isinstance(empty, pd.DataFrame)
    assert list(empty.columns) == ["id", "name", "level_id", "level_name"]
    assert len(empty) == 0
    assert "No localities found" in capsys.readouterr().err
