"""Data Explorer — MCP server for Week 5.

Wraps an open country dataset and exposes it to an agent as MCP tools over STDIO:
`search_countries` (find countries by name) and `get_country_details` (currencies,
languages, borders and flag for one country).

Data source: the open `mledoze/countries` dataset (the data REST Countries was built
on), served as one JSON file from GitHub. No API key. It is fetched over HTTPS on the
first call and cached in memory.

Every failure comes back as data, never as an exception that kills the server:
    {"error": "<what went wrong>", "retryable": true|false}
`retryable` tells the agent whether calling again could help (timeouts, 5xx) or not
(bad input, unknown country).

Setup:
    pip install -r requirements.txt
Run (STDIO) — register this command in your MCP client (e.g. Claude Desktop / an IDE):
    python server.py
"""
import unicodedata

import httpx
from mcp.server.fastmcp import FastMCP

DATA_URL = "https://raw.githubusercontent.com/mledoze/countries/master/countries.json"
# Each country has a 3-letter `cca3` code; its flag lives at this URL (lowercase file names).
FLAG_URL = "https://raw.githubusercontent.com/mledoze/countries/master/data/{cca3}.svg"
TIMEOUT_SECONDS = 15
MAX_LIMIT = 20
MAX_TEXT = 80

mcp = FastMCP("data-explorer")

_countries: list[dict] | None = None  # in-memory cache of the dataset


class DataError(Exception):
    """The dataset could not be loaded. `retryable` says whether trying again may help."""

    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


def error(message: str, retryable: bool = False) -> dict:
    return {"error": message, "retryable": retryable}


def load_countries() -> list[dict]:
    """Download the dataset once and cache it. Raises DataError on any failure."""
    global _countries
    if _countries is not None:
        return _countries
    try:
        resp = httpx.get(DATA_URL, timeout=TIMEOUT_SECONDS, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException as exc:
        raise DataError(f"country data source timed out after {TIMEOUT_SECONDS}s", retryable=True) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise DataError(f"country data source returned HTTP {status}", retryable=status >= 500) from exc
    except httpx.HTTPError as exc:
        raise DataError(f"could not reach country data source ({type(exc).__name__})", retryable=True) from exc
    except ValueError as exc:
        raise DataError("country data source returned invalid JSON", retryable=True) from exc
    # Only cache a payload of the expected shape, so one bad response is not stuck in memory
    if not isinstance(data, list) or not all(isinstance(c, dict) and "name" in c for c in data):
        raise DataError("country data source returned data in an unexpected format", retryable=True)
    _countries = data
    return _countries


def fold(text: str) -> str:
    """Lowercase and strip accents, so 'turkiye' finds 'Türkiye' and 'curacao' finds 'Curaçao'."""
    decomposed = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def check_text(value: object, field: str) -> str | None:
    """Return a problem description if `value` is not a usable search string."""
    if not isinstance(value, str):
        return f"{field} must be a string"
    if not value.strip():
        return f"{field} must not be empty"
    if len(value.strip()) > MAX_TEXT:
        return f"{field} must be at most {MAX_TEXT} characters"
    return None


def names_of(country: dict) -> list[str]:
    """Every name an agent might use for a country: common, official, ISO codes, alternatives."""
    name = country.get("name") or {}
    names = [name.get("common"), name.get("official"), country.get("cca2"), country.get("cca3")]
    names += country.get("altSpellings") or []
    return [fold(n) for n in names if isinstance(n, str) and n]


@mcp.tool()
def search_countries(query: str, limit: int = 5) -> list[dict]:
    """Search countries by name. Returns a list of {name, capital, region, subregion}.

    Matches part of the common or official name, ignoring case and accents
    ("turk" finds Türkiye). `limit` is 1-20. An empty list means nothing matched.
    On failure the list holds one {"error", "retryable"} item.
    """
    problem = check_text(query, "query")
    if problem:
        return [error(problem)]
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        return [error(f"limit must be a whole number from 1 to {MAX_LIMIT}")]
    try:
        countries = load_countries()
    except DataError as exc:
        return [error(str(exc), exc.retryable)]

    q = fold(query)
    matches = [
        c for c in countries
        if q in fold(c["name"]["common"]) or q in fold(c["name"]["official"])
    ]
    # No matches is not an error: return an empty list.
    results = []
    for c in matches[:limit]:
        results.append(
            {
                "name": c["name"]["common"],
                "capital": (c.get("capital") or [None])[0],
                "region": c.get("region"),
                "subregion": c.get("subregion"),
            }
        )
    return results


@mcp.tool()
def get_country_details(name: str) -> dict:
    """Get currencies, languages, borders and the flag URL for one country.

    `name` may be the common or official name, a 2- or 3-letter ISO code, or a common
    alternative ("UK", "USA", "Turkiye"); case and accents are ignored. An exact match
    wins; otherwise one partial match is accepted. If several countries match, the error
    lists them in "candidates" so you can call again with one of those names.
    """
    problem = check_text(name, "name")
    if problem:
        return error(problem)
    try:
        countries = load_countries()
    except DataError as exc:
        return error(str(exc), exc.retryable)

    q = fold(name)
    exact = [c for c in countries if q in names_of(c)]
    found = exact or [c for c in countries if any(q in n for n in names_of(c))]
    if not found:
        return error(f"no country matches '{name.strip()}'; try search_countries first")
    if len(found) > 1:
        # Most relevant first: the query in the common name, then the official name, then
        # only in an alternative spelling ("land" matches "...Islands" in many altSpellings)
        def relevance(c: dict) -> tuple[int, str]:
            common = fold(c["name"]["common"])
            rank = 0 if q in common else 1 if q in fold(c["name"].get("official") or "") else 2
            return rank, common

        result = error(f"'{name.strip()}' matches {len(found)} countries; call again with one of the candidates")
        result["candidates"] = [c["name"]["common"] for c in sorted(found, key=relevance)][:MAX_LIMIT]
        return result

    country = found[0]
    name_by_code = {c.get("cca3"): c["name"]["common"] for c in countries}
    cca3 = country.get("cca3") or ""
    return {
        "name": country["name"]["common"],
        "official_name": country["name"].get("official"),
        "code": cca3,
        "currencies": [
            {"code": code, "name": info.get("name"), "symbol": info.get("symbol")}
            for code, info in (country.get("currencies") or {}).items()
        ],
        "languages": sorted((country.get("languages") or {}).values()),
        "borders": [
            {"code": code, "name": name_by_code.get(code, code)} for code in country.get("borders") or []
        ],
        "flag_url": FLAG_URL.format(cca3=cca3.lower()) if cca3 else None,
    }


if __name__ == "__main__":
    mcp.run()
