# Getting started

## Installation

```bash
pip install ibgepy
```

Requires Python 3.9+, `requests` and `pandas`.

## Fetching data

`ibge_variables()` is the main function. It returns a tidy (long)
`pandas.DataFrame`.

```python
import ibgepy

# IPCA in Brazil (aggregate 7060), last 6 periods (default)
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

### Argument forms

| Argument | Accepts |
|----------|---------|
| `variable` | `None` (standard), an id or list of ids, or `"all"` |
| `periods` | negative int (last-N), a value/list, or a range string `"201701-201712"` |
| `localities` | `"BR"`, a level code (`"N3"`), or a mapping `{"N6": [3550308, 3304557]}` |
| `classification` | mapping of classification id → category id(s), or `"all"` |

## Converting values

The `value` column comes back as strings because IBGE uses special codes
(`-`, `..`, `...`, `X`). Convert with `parse_ibge_value()`:

```python
df["value"] = ibgepy.parse_ibge_value(df["value"])
```

- `"-"` → `0` (numeric zero, not rounding)
- `".."`, `"..."`, `"X"` → `NaN`

## Quieter output

Functions print progress/success messages to stderr (like the R package's
cli alerts). Silence them globally:

```python
ibgepy.set_verbose(False)
```
