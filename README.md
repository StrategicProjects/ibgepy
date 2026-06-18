# ibgepy

[![PyPI](https://img.shields.io/pypi/v/ibgepy.svg)](https://pypi.org/project/ibgepy/)
[![Python versions](https://img.shields.io/pypi/pyversions/ibgepy.svg)](https://pypi.org/project/ibgepy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Access the IBGE Aggregate Data API (SIDRA) from Python.**

`ibgepy` is a pandas-friendly interface to the [IBGE aggregate data
API](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3) of the
Brazilian Institute of Geography and Statistics (IBGE). Query aggregates,
variables, localities, periods, subjects, surveys and metadata from the
surveys and censuses conducted by IBGE — every fetch returns a
`pandas.DataFrame`.

This is the Python port of the R package
[`ibger`](https://github.com/StrategicProjects/ibger); the public function
names mirror the R API so knowledge transfers directly between the two.

## Installation

```bash
pip install ibgepy
```

Requires Python 3.9+, `requests` and `pandas`.

## Quick start

```python
import ibgepy

# IPCA in Brazil (aggregate 7060), last 6 periods
df = ibgepy.ibge_variables(7060, localities="BR")

# Specific variables for all states
ibgepy.ibge_variables(1705, variable=[284, 285], localities="N3")

# Specific municipalities (São Paulo, Rio) with a classification
ibgepy.ibge_variables(
    aggregate=1712,
    variable=214,
    periods=-3,
    localities={"N6": [3550308, 3304557]},
    classification={"226": [4844, 96608]},
)
```

The `value` column comes back as strings (IBGE uses special codes such as
`-`, `..`, `...`, `X`). Convert it with `parse_ibge_value`:

```python
df["value"] = ibgepy.parse_ibge_value(df["value"])
```

## Discover what to query

```python
ibgepy.ibge_aggregates(periodicity="P5")   # list monthly tables
ibgepy.ibge_metadata(7060)                  # full metadata for a table
ibgepy.ibge_periods(1705)                   # available periods
ibgepy.ibge_localities(1437, level="N6")    # localities at a level
ibgepy.ibge_subjects("internet")            # built-in subject-code lookup
```

`ibge_metadata()` returns an `IbgeMetadata` object whose `.variables` and
`.classifications` are DataFrames (the `categories` column holds a nested
DataFrame per classification).

## Survey catalog (Metadata API v2)

```python
ibgepy.ibge_surveys()                       # institutional survey catalog
ibgepy.ibge_survey_periods("SC")            # periods with metadata
ibgepy.ibge_survey_metadata("CD", year=2022)
```

## Coming from SIDRA URLs

Already have a SIDRA API URL (e.g. from the SIDRA Query Builder or the R
`sidrar` package)? Inspect or run it directly:

```python
url = "https://apisidra.ibge.gov.br/values/t/7060/n1/all/v/63/p/last%2012/c315/7169"

ibgepy.parse_sidra_url(url)   # human-readable breakdown + equivalent call
ibgepy.fetch_sidra_url(url)   # fetch as a tidy DataFrame
```

## Caching and messages

Metadata and the survey catalog are cached in memory per session. Clear it
with `ibgepy.ibge_clear_cache()`. Silence the progress/success messages with
`ibgepy.set_verbose(False)`.

## Public API

| Function | Purpose |
|----------|---------|
| `ibge_variables` | Fetch variable data (main function) |
| `ibge_aggregates` | List aggregates (tables) |
| `ibge_metadata` | Full aggregate metadata |
| `ibge_periods` | Available periods |
| `ibge_localities` | Localities at given levels |
| `ibge_subjects` | Built-in subject-code lookup |
| `ibge_surveys` / `ibge_survey_periods` / `ibge_survey_metadata` | Survey catalog (Metadata API v2) |
| `parse_ibge_value` | Convert IBGE value codes to numeric |
| `parse_sidra_url` / `fetch_sidra_url` | Translate/execute SIDRA URLs |
| `ibge_clear_cache` | Clear the in-memory cache |
| `set_verbose` | Toggle console messages |

## License

MIT — see [LICENSE](LICENSE). Developed by the ibgepy authors.
