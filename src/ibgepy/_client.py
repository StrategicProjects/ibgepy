"""HTTP layer for the two IBGE APIs.

* Aggregates API v3 — :data:`AGGREGATES_URL`
* Metadata API v2   — :data:`METADATA_URL`

Both helpers retry transient failures (mirroring ``httr2::req_retry``) and
raise :class:`IbgeError` with a friendly message on failure.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 ships with requests; import path is stable
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

from . import _msg

AGGREGATES_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"
METADATA_URL = "https://servicodados.ibge.gov.br/api/v2/metadados"

_USER_AGENT = "ibgepy (Python package)"
_TIMEOUT = 60


class IbgeError(RuntimeError):
    """Raised when an IBGE API request fails."""


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": _USER_AGENT})
    return session


def _http_error_hint(status: int, data_request: bool = False) -> str:
    """Explain an HTTP error status.

    The Aggregates API answers 500 both to oversized data queries and to
    requests it cannot interpret (a non-existent aggregate id, an invalid
    filter value). The size-limit hint only makes sense for the data endpoint.
    """
    if status != 500:
        return f"HTTP error {status}"
    if data_request:
        return (
            "The API returned error 500. This usually means the query exceeds "
            "the API's result-size limit (documented as 100,000 values, in "
            "practice around 50,000). Try reducing localities, periods or "
            "categories, or let chunk=True split the request automatically."
        )
    return (
        "The API returned error 500. The IBGE API responds with 500 when it "
        "cannot interpret a request, e.g. a non-existent aggregate id or an "
        "invalid filter value. Check the parameters."
    )


def _perform(
    url: str,
    query: Optional[Mapping[str, Any]],
    label: str,
    api_name: str,
    data_request: bool = False,
) -> Any:
    clean_query = {k: v for k, v in (query or {}).items() if v is not None}
    _msg.step(f"Fetching {label} from {api_name}...")
    try:
        resp = _session().get(url, params=clean_query, timeout=_TIMEOUT)
    except requests.RequestException as exc:
        raise IbgeError(
            f"Failed to access the {api_name}.\n  x {exc}\n  i URL: {url}"
        ) from exc

    if resp.status_code >= 400:
        detail = _http_error_hint(resp.status_code, data_request)
        raise IbgeError(f"{detail}\n  i URL: {resp.url}")

    return resp.json()


def ibge_request(
    *path: Any,
    query: Optional[Mapping[str, Any]] = None,
    label: str = "data",
    data_request: bool = False,
) -> Any:
    """Build and execute a request against the Aggregates API (v3).

    ``data_request=True`` marks calls to the ``variaveis`` endpoint, where an
    HTTP 500 usually means the result is too large; other endpoints answer
    500 to invalid parameters, so they get a different hint.
    """
    segments = [str(p) for p in path]
    url = "/".join([AGGREGATES_URL, *segments])
    return _perform(url, query, label, "IBGE API", data_request=data_request)


def metadata_request(*path: Any, label: str = "data") -> Any:
    """Build and execute a request against the Metadata API (v2)."""
    segments = [str(p) for p in path]
    url = "/".join([METADATA_URL, *segments])
    return _perform(url, None, label, "IBGE Metadata API")
