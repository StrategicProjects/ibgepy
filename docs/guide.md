# User guide

## Discovering what to query

```python
import ibgepy

ibgepy.ibge_aggregates(periodicity="P5")   # list monthly tables
ibgepy.ibge_aggregates(level="N6")          # tables available at municipality level
ibgepy.ibge_periods(1705)                   # available periods for an aggregate
ibgepy.ibge_localities(1437, level="N6")    # localities at a level
ibgepy.ibge_subjects("internet")            # built-in subject-code lookup (no API call)
```

## Aggregate metadata

`ibge_metadata()` returns an `IbgeMetadata` object describing a table —
its variables, classifications (with every category), territorial levels and
periodicity.

```python
meta = ibgepy.ibge_metadata(7060)
meta.variables          # DataFrame: id, name, unit
meta.classifications    # DataFrame: id, name, categories (nested DataFrame)
meta.periodicity        # {"frequency", "start", "end"}
meta.territorial_level  # {"administrative", "special", "ibge"}
```

Each row of `meta.classifications` holds, in its `categories` cell, a nested
DataFrame with `category_id`, `category_name`, `category_unit`,
`category_level`.

## Survey catalog (Metadata API v2)

These functions query a **different** IBGE API — the Metadata API (v2),
which documents the surveys (statistical operations) themselves.

```python
ibgepy.ibge_surveys()                         # institutional survey catalog
ibgepy.ibge_survey_periods("SC")              # periods with metadata
ibgepy.ibge_survey_metadata("CD", year=2022)  # structural survey (no month)
ibgepy.ibge_survey_metadata("SC", year=2023, month=6)  # conjunctural survey
```

Invalid survey codes raise a helpful error suggesting the closest matches.

## Coming from SIDRA URLs

Already have a SIDRA API URL (from the SIDRA Query Builder or the R `sidrar`
package)? Inspect or run it directly.

```python
url = "https://apisidra.ibge.gov.br/values/t/7060/n1/all/v/63/p/last%2012/c315/7169"

ibgepy.parse_sidra_url(url)   # human-readable breakdown + equivalent ibge_variables() call
ibgepy.fetch_sidra_url(url)   # fetch as a tidy DataFrame
```

## Caching

Aggregate metadata and the survey catalog are cached in memory per session,
so repeated calls are instant. Reset with:

```python
ibgepy.ibge_clear_cache()
```

## Errors

- `ibgepy.IbgeError` — a request to the IBGE API failed (network or HTTP).
- `ibgepy.ValidationError` — a parameter did not match the aggregate
  metadata (raised before any request, when `validate=True`). Pass
  `validate=False` to skip pre-flight checks.
