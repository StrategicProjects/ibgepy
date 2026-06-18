from ibgepy import ibge_subjects


def test_subjects_full_table():
    df = ibge_subjects()
    assert len(df) == 254
    assert list(df.columns) == ["id", "name"]
    assert df["id"].dtype.kind in ("i", "u")


def test_subjects_pattern():
    df = ibge_subjects("internet")
    assert len(df) >= 1
    assert df["name"].str.contains("internet", case=False).all()


def test_subjects_accents_preserved():
    df = ibge_subjects()
    names = set(df["name"])
    assert "Saúde" in names
    assert "Abate de animais" in names
