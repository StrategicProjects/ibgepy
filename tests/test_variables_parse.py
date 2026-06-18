from ibgepy.variables import _parse_variables


def test_parse_default_nested():
    data = [
        {
            "id": "63",
            "variavel": "IPCA - Variação mensal",
            "unidade": "%",
            "resultados": [
                {
                    "classificacoes": [
                        {"id": "315", "categoria": {"7169": "Geral"}}
                    ],
                    "series": [
                        {
                            "localidade": {
                                "id": "1",
                                "nome": "Brasil",
                                "nivel": {"id": "N1", "nome": "Brasil"},
                            },
                            "serie": {"202401": "0.42", "202402": "0.83"},
                        }
                    ],
                }
            ],
        }
    ]
    df = _parse_variables(data)
    assert len(df) == 2
    assert df["variable_id"].iloc[0] == "63"
    assert df["classification_315"].iloc[0] == "Geral"
    assert df["locality_name"].iloc[0] == "Brasil"
    assert set(df["period"]) == {"202401", "202402"}
    assert df["value"].tolist() == ["0.42", "0.83"]


def test_parse_flat_header_and_rows():
    data = [
        {"NC": "Nível", "NN": "Nome", "V": "Valor", "D1C": "Cód", "D1N": "Período"},
        {"NC": "1", "NN": "Brasil", "V": "0.42", "D1C": "202401", "D1N": "janeiro 2024"},
    ]
    df = _parse_variables(data, view="flat")
    assert len(df) == 1
    assert "Valor" in df.columns
    assert df["Valor"].iloc[0] == "0.42"


def test_parse_empty():
    assert _parse_variables([]).empty
