# Week 5 Writeup: Data Explorer MCP Server

- **Server:** `server.py`, two tools: `search_countries` (the worked example, hardened) and
  `get_country_details` (new).
- **Client:** Claude Code, with the server registered through an MCP config (`data-explorer`, status
  `connected`). The full session is in [`agent_session.md`](agent_session.md).
- **Tests:** 37 passing, no network needed (`python -m pytest`).

## Transcript: an agent calling both tools

I asked the agent to plan a trip to Turkey and its neighbours, find the euro-using neighbour, look at
"the Stans", and try a fictional country. It made 11 tool calls. The main ones (results shortened):

```text
get_country_details({"name": "Turkey"})
→ {"name": "Türkiye", "code": "TUR", "currencies": [{"code": "TRY", "name": "Turkish lira", "symbol": "₺"}],
   "languages": ["Turkish"], "borders": [{"code": "ARM", "name": "Armenia"}, … {"code": "SYR", "name": "Syria"}], …}

search_countries({"query": "stan", "limit": 20})
→ [{"name": "Afghanistan", …}, {"name": "Saint Helena, Ascension and Tristan da Cunha", …},
   {"name": "Kazakhstan", …}, …]

get_country_details({"name": "Greece"})
→ {"name": "Greece", "currencies": [{"code": "EUR", "name": "Euro", "symbol": "€"}], …}

get_country_details({"name": "Wakanda"})
→ {"error": "no country matches 'Wakanda'; try search_countries first", "retryable": false}
```

Two things the transcript shows:

- **"Turkey" resolved** even though the dataset's name is "Türkiye". The tool also checks the ISO codes
  and the dataset's alternative spellings, and ignores accents.
- **The agent filtered the search itself.** `"stan"` also matched "Tri**stan** da Cunha"; the agent
  left it out of "the Stans", then called `get_country_details` for each of the seven real ones to read
  their borders. It found that Afghanistan, Pakistan and Turkmenistan border Iran, one of Turkey's
  neighbours. The tool returned the raw match and the agent did the reasoning.

## How I handled errors

Every failure is returned as data with the same shape, `{"error": "...", "retryable": true|false}`, so
the server never crashes and the agent can decide whether to retry, rephrase, or stop. Outputs from the
real server:

| Call | Result |
| --- | --- |
| `search_countries("   ")` | `[{"error": "query must not be empty", "retryable": false}]` |
| `search_countries("ger", limit=0)` | `[{"error": "limit must be a whole number from 1 to 20", "retryable": false}]` |
| `search_countries("zzzz")` | `[]` (no match is not an error) |
| `get_country_details("Wakanda")` | `{"error": "no country matches 'Wakanda'; try search_countries first", "retryable": false}` |
| `get_country_details("guin")` | `{"error": "'guin' matches 4 countries; …", "retryable": false, "candidates": ["Equatorial Guinea", "Guinea", …]}` |
| `get_country_details("Japan")`, data source times out | `{"error": "country data source timed out after 15s", "retryable": true}` |
| `get_country_details("Japan")`, data source returns 404 | `{"error": "country data source returned HTTP 404", "retryable": false}` |
| `get_country_details("Japan")`, next call after the network is back | `{"name": "Japan", "code": "JPN", …}` |

- **Input** is checked before any network call: type, empty or whitespace-only text, length, and
  `limit` (a `bool` or a string like `"3"` is rejected).
- **Upstream failures** are split by cause: timeout, connection error, HTTP status (5xx retryable, 4xx
  not), invalid JSON, and a payload that is not a list of countries.
- **A failed download is not cached.** In the starter, a response that was not JSON raised an uncaught
  `JSONDecodeError` (only `httpx.HTTPError` was caught), and valid JSON of the wrong shape was cached
  for the rest of the session. Now only a valid list is kept, so the next call can recover.
- **Ambiguity is not a guess.** An exact match wins (so `Congo` and `Niger` are not confused with
  `DR Congo` and `Nigeria`). Several partial matches return `candidates`, most relevant first: testing
  `"land"` on real data showed that alphabetical order filled the list with countries that matched only
  in an alternative spelling ("Islands") and pushed Finland and Poland out.
- **Missing fields** (85 countries have no borders, 4 have no currency) become empty lists or `null`,
  never a `KeyError`.

## What I learned

My most important takeaway this week was that presenting the information a task needs in a clear form matters more than giving the agent more data. When the "stan" search also returned Tristan da Cunha, it showed that the server can find matches, but judging whether the results fit the task is left to the agent. Solving things on the server, such as matching Turkey to Türkiye and adding names to the neighbour codes, kept the agent from making unnecessary calls. Next time I design a tool, I will pay attention not only to the fields it returns but also to the order of the results and to stating clearly whether an error can be retried.
