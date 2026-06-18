# ibgepy

**Access the IBGE Aggregate Data API (SIDRA) from Python.**

`ibgepy` is a [pandas](https://pandas.pydata.org/)-friendly interface to the
[IBGE aggregate data API](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3)
of the Brazilian Institute of Geography and Statistics (IBGE). Query
aggregates, variables, localities, periods, subjects, surveys and metadata
from the surveys and censuses conducted by IBGE — every fetch returns a
`pandas.DataFrame`.

It is the Python port of the R package
[`ibger`](https://github.com/StrategicProjects/ibger); the public function
names mirror the R API so knowledge transfers directly between the two.

## Install

```bash
pip install ibgepy
```

## A first query

```python
import ibgepy

# IPCA in Brazil (aggregate 7060), last 6 periods
df = ibgepy.ibge_variables(7060, localities="BR")

# The value column is text (IBGE special codes); convert to numeric
df["value"] = ibgepy.parse_ibge_value(df["value"])
```

Continue with the [Getting started](getting-started.md) guide, the
[User guide](guide.md), or jump to the full [API reference](reference.md).

## Highlights

- **Tidy output** — every public function returns a `pandas.DataFrame`.
- **Pre-flight validation** — query parameters are checked against the
  aggregate metadata before the request is sent, with clear errors.
- **In-memory caching** — metadata and the survey catalog are cached per
  session; clear with `ibge_clear_cache()`.
- **SIDRA URL migration** — translate or run SIDRA API URLs directly with
  `parse_sidra_url()` / `fetch_sidra_url()`.
