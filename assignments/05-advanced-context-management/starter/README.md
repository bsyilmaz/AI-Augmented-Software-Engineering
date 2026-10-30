# Data Explorer MCP Server

A `FastMCP` server over the open, no-key **[mledoze/countries](https://github.com/mledoze/countries)**
dataset (the data REST Countries was built on). It gives an agent two tools: search for countries
by name, and get the currencies, languages, borders and flag of one country.

The dataset is one JSON file fetched over HTTPS on the first call and cached in memory, so timeouts
and HTTP errors are real failure modes. Both tools return them as data instead of crashing.

## Install

Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

## Run (STDIO)

```bash
python server.py
```

The server speaks MCP over STDIO. It prints nothing and waits for a client; that is normal. Stop it
with Ctrl+C.

## Register in an MCP client

Use absolute paths. If you installed into a virtual environment, point `command` at that
environment's `python`.

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "data-explorer": { "command": "python", "args": ["/absolute/path/to/server.py"] }
  }
}
```

**Claude Code:**

```bash
claude mcp add data-explorer -- python /absolute/path/to/server.py
```

or pass the same JSON as a file with `claude --mcp-config mcp.json`. The tools then appear as
`mcp__data-explorer__search_countries` and `mcp__data-explorer__get_country_details`.

## Tool reference

### `search_countries(query, limit=5)`

Finds countries whose common or official name contains `query`, ignoring case and accents.

| Parameter | Type | Rules |
| --- | --- | --- |
| `query` | string | Required, 1 to 80 characters after trimming |
| `limit` | integer | 1 to 20, default 5 |

Returns a list of `{name, capital, region, subregion}`. No match is an empty list, not an error.

```text
search_countries("turk", limit=3)
→ [{"name": "Turks and Caicos Islands", "capital": "Cockburn Town", "region": "Americas", "subregion": "Caribbean"},
   {"name": "Turkmenistan", "capital": "Ashgabat", "region": "Asia", "subregion": "Central Asia"},
   {"name": "Türkiye", "capital": "Ankara", "region": "Asia", "subregion": "Western Asia"}]
```

Results keep the dataset's order. Note that `"turk"` without the accent still finds `Türkiye`.

### `get_country_details(name)`

Returns details for one country. `name` can be the common or official name, a 2- or 3-letter ISO code,
or a common alternative spelling such as `UK`, `USA`, `DRC` or `Turkiye`. An exact match wins; otherwise
a single partial match is accepted.

| Parameter | Type | Rules |
| --- | --- | --- |
| `name` | string | Required, 1 to 80 characters after trimming |

Returns `{name, official_name, code, currencies, languages, borders, flag_url}`:

```text
get_country_details("Turkey")
→ {"name": "Türkiye", "official_name": "Republic of Türkiye", "code": "TUR",
   "currencies": [{"code": "TRY", "name": "Turkish lira", "symbol": "₺"}],
   "languages": ["Turkish"],
   "borders": [{"code": "ARM", "name": "Armenia"}, {"code": "AZE", "name": "Azerbaijan"}, …],
   "flag_url": "https://raw.githubusercontent.com/mledoze/countries/master/data/tur.svg"}
```

If several countries match, the error lists `candidates`, most relevant first (the query in the
common name, then the official name, then an alternative spelling):

```text
get_country_details("guin")
→ {"error": "'guin' matches 4 countries; call again with one of the candidates", "retryable": false,
   "candidates": ["Equatorial Guinea", "Guinea", "Guinea-Bissau", "Papua New Guinea"]}
```

### Errors

Both tools return failures as `{"error": "...", "retryable": true|false}` (inside a one-item list for
`search_countries`). `retryable` is `true` for timeouts, network errors, HTTP 5xx and a malformed
payload, and `false` for invalid input, an unknown country and HTTP 4xx. A failed download is not
cached, so the next call tries again.

## Tests

```bash
pip install pytest
python -m pytest
```

The 37 tests replace `httpx.get` with fakes, so they need no network.

## Files

- `server.py`: the MCP server and both tools
- `tests/test_server.py`: input validation, matching, missing fields, and every upstream failure
- `agent_session.md`: Claude Code using both tools through this server
- `writeup.md`: transcript summary, error handling, what I learned
