"""Tests for the Data Explorer tools. No network: httpx.get is replaced with fakes."""
import httpx
import pytest

import server

GERMANY = {
    "name": {"common": "Germany", "official": "Federal Republic of Germany"},
    "cca2": "DE",
    "cca3": "DEU",
    "capital": ["Berlin"],
    "region": "Europe",
    "subregion": "Western Europe",
    "currencies": {"EUR": {"name": "Euro", "symbol": "€"}},
    "languages": {"deu": "German"},
    "borders": ["AUT", "POL", "XXX"],
    "altSpellings": ["DE", "Bundesrepublik Deutschland"],
}
AUSTRIA = {
    "name": {"common": "Austria", "official": "Republic of Austria"},
    "cca2": "AT",
    "cca3": "AUT",
    "capital": ["Vienna"],
    "region": "Europe",
    "currencies": {"EUR": {"name": "Euro", "symbol": "€"}},
    "languages": {"bar": "Austro-Bavarian German", "deu": "German"},
    "borders": ["DEU"],
    "altSpellings": ["AT"],
}
POLAND = {"name": {"common": "Poland", "official": "Republic of Poland"}, "cca2": "PL", "cca3": "POL"}
TURKIYE = {
    "name": {"common": "Türkiye", "official": "Republic of Türkiye"},
    "cca2": "TR",
    "cca3": "TUR",
    "altSpellings": ["TR", "Turkiye", "Republic of Turkey"],
}
CONGO = {"name": {"common": "Congo", "official": "Republic of the Congo"}, "cca2": "CG", "cca3": "COG"}
DR_CONGO = {
    "name": {"common": "DR Congo", "official": "Democratic Republic of the Congo"},
    "cca2": "CD",
    "cca3": "COD",
    "altSpellings": ["DRC"],
}
# A territory with no capital, currency, language or borders
ISLAND = {"name": {"common": "Bouvet Island", "official": "Bouvet Island"}, "cca2": "BV", "cca3": "BVT"}
DATA = [GERMANY, AUSTRIA, POLAND, TURKIYE, CONGO, DR_CONGO, ISLAND]


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setattr(server, "_countries", None)


def serve(monkeypatch, payload=DATA, status=200):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return httpx.Response(status, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(server.httpx, "get", fake_get)
    return calls


def fail_with(monkeypatch, exc):
    def fake_get(url, **kwargs):
        raise exc

    monkeypatch.setattr(server.httpx, "get", fake_get)


# --- search_countries -------------------------------------------------------------


def test_search_returns_model_friendly_rows(monkeypatch):
    serve(monkeypatch)
    assert server.search_countries("germ") == [
        {"name": "Germany", "capital": "Berlin", "region": "Europe", "subregion": "Western Europe"}
    ]


def test_search_ignores_case_and_accents(monkeypatch):
    serve(monkeypatch)
    assert [r["name"] for r in server.search_countries("TURKIYE")] == ["Türkiye"]


def test_search_no_match_is_an_empty_list_not_an_error(monkeypatch):
    serve(monkeypatch)
    assert server.search_countries("atlantis") == []


def test_search_respects_limit(monkeypatch):
    serve(monkeypatch)
    assert len(server.search_countries("republic", limit=2)) == 2


def test_search_handles_missing_fields(monkeypatch):
    serve(monkeypatch)
    assert server.search_countries("bouvet") == [
        {"name": "Bouvet Island", "capital": None, "region": None, "subregion": None}
    ]


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [
        ("", 5, "query must not be empty"),
        ("   ", 5, "query must not be empty"),
        (None, 5, "query must be a string"),
        ("x" * 81, 5, "query must be at most 80 characters"),
        ("ger", 0, "limit must be a whole number from 1 to 20"),
        ("ger", 21, "limit must be a whole number from 1 to 20"),
        ("ger", "3", "limit must be a whole number from 1 to 20"),
        ("ger", True, "limit must be a whole number from 1 to 20"),
    ],
)
def test_search_rejects_bad_input_without_fetching(monkeypatch, query, limit, message):
    calls = serve(monkeypatch)
    assert server.search_countries(query, limit) == [{"error": message, "retryable": False}]
    assert calls == []


# --- get_country_details ------------------------------------------------------------


def test_details_have_currencies_languages_borders_and_flag(monkeypatch):
    serve(monkeypatch)
    assert server.get_country_details("Germany") == {
        "name": "Germany",
        "official_name": "Federal Republic of Germany",
        "code": "DEU",
        "currencies": [{"code": "EUR", "name": "Euro", "symbol": "€"}],
        "languages": ["German"],
        # Unknown neighbour codes are kept rather than dropped
        "borders": [
            {"code": "AUT", "name": "Austria"},
            {"code": "POL", "name": "Poland"},
            {"code": "XXX", "name": "XXX"},
        ],
        "flag_url": "https://raw.githubusercontent.com/mledoze/countries/master/data/deu.svg",
    }


@pytest.mark.parametrize(
    "name", ["germany", "Federal Republic of Germany", "DE", "deu", "Bundesrepublik Deutschland"]
)
def test_details_accept_names_codes_and_alternatives(monkeypatch, name):
    serve(monkeypatch)
    assert server.get_country_details(name)["code"] == "DEU"


@pytest.mark.parametrize("name", ["Turkiye", "türkiye", "Turkey"])
def test_details_find_turkiye_by_common_spellings(monkeypatch, name):
    serve(monkeypatch)
    assert server.get_country_details(name)["code"] == "TUR"


def test_exact_match_wins_over_partial_matches(monkeypatch):
    serve(monkeypatch)
    # "Congo" is also part of "DR Congo", but it is the exact name of Congo-Brazzaville
    assert server.get_country_details("Congo")["code"] == "COG"
    assert server.get_country_details("DRC")["code"] == "COD"


def test_ambiguous_name_lists_candidates(monkeypatch):
    serve(monkeypatch)
    result = server.get_country_details("republic")
    assert result["retryable"] is False
    assert "matches" in result["error"]
    assert {"Germany", "Austria", "Poland"} <= set(result["candidates"])


def test_candidates_list_name_matches_before_alternative_spellings(monkeypatch):
    island = {
        "name": {"common": "Bermuda", "official": "Bermuda"},
        "cca3": "BMU",
        "altSpellings": ["The Islands of Bermuda"],
    }
    finland = {"name": {"common": "Finland", "official": "Republic of Finland"}, "cca3": "FIN"}
    serve(monkeypatch, payload=[island, POLAND, finland])
    # "land" is in Finland and Poland, and only in Bermuda's alternative spelling "Islands"
    assert server.get_country_details("land")["candidates"] == ["Finland", "Poland", "Bermuda"]


def test_unknown_country_is_a_clean_error(monkeypatch):
    serve(monkeypatch)
    assert server.get_country_details("Atlantis") == {
        "error": "no country matches 'Atlantis'; try search_countries first",
        "retryable": False,
    }


def test_details_handle_missing_fields(monkeypatch):
    serve(monkeypatch)
    details = server.get_country_details("Bouvet Island")
    assert details["currencies"] == [] and details["languages"] == [] and details["borders"] == []


@pytest.mark.parametrize(("name", "message"), [("", "name must not be empty"), (42, "name must be a string")])
def test_details_reject_bad_input(monkeypatch, name, message):
    serve(monkeypatch)
    assert server.get_country_details(name) == {"error": message, "retryable": False}


# --- upstream failures (both tools) ---------------------------------------------------


@pytest.mark.parametrize(
    ("setup", "message", "retryable"),
    [
        (lambda mp: fail_with(mp, httpx.ReadTimeout("slow")), "timed out after 15s", True),
        (lambda mp: fail_with(mp, httpx.ConnectError("no network")), "could not reach", True),
        (lambda mp: serve(mp, status=503), "returned HTTP 503", True),
        (lambda mp: serve(mp, status=404), "returned HTTP 404", False),
        (lambda mp: serve(mp, payload={"oops": True}), "unexpected format", True),
    ],
)
def test_upstream_failures_become_structured_errors(monkeypatch, setup, message, retryable):
    setup(monkeypatch)
    [search] = server.search_countries("germany")
    details = server.get_country_details("germany")
    for result in (search, details):
        assert message in result["error"]
        assert result["retryable"] is retryable


def test_invalid_json_is_a_structured_error(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(200, content=b"<html>not json", request=httpx.Request("GET", url))

    monkeypatch.setattr(server.httpx, "get", fake_get)
    assert server.get_country_details("germany")["error"] == "country data source returned invalid JSON"


def test_a_failure_is_not_cached_and_the_next_call_recovers(monkeypatch):
    fail_with(monkeypatch, httpx.ReadTimeout("slow"))
    assert "error" in server.get_country_details("germany")
    serve(monkeypatch)
    assert server.get_country_details("germany")["code"] == "DEU"


def test_dataset_is_fetched_once_and_cached(monkeypatch):
    calls = serve(monkeypatch)
    server.search_countries("germ")
    server.get_country_details("Austria")
    assert len(calls) == 1
