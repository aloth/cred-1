"""Tests for the cred1 Python package. They read the dataset in data/ when run
from a checkout and the bundled copy when run against an installed wheel."""
import json
from pathlib import Path

import pytest

import cred1

DATA = json.loads((Path(__file__).resolve().parents[2] / "data" / "cred1_compact.json").read_text(encoding="utf-8"))


def test_normalize_domain_strips_protocol_www_path_and_case():
    assert cred1.normalize_domain("  HTTPS://www.Example.COM/a/b?x=1#y ") == "example.com"
    assert cred1.normalize_domain("example.com.") == "example.com"


def test_check_returns_the_bundled_entry_for_a_url():
    domain, entry = next(iter(DATA.items()))
    result = cred1.check(f"https://www.{domain}/article")
    assert result["domain"] == domain
    assert result["score"] == entry["s"]
    assert result["sources"] == entry["n"]
    assert result["category"] in {"fake", "unreliable", "mixed", "conspiracy", "satire", "rumor", "other"}


def test_check_returns_none_for_an_unlisted_domain():
    assert cred1.check("this-domain-is-not-in-cred1.invalid") is None


def test_check_many_keeps_the_inputs_as_keys():
    domain = next(iter(DATA))
    out = cred1.check_many([domain, "unlisted.invalid"])
    assert out[domain]["domain"] == domain
    assert out["unlisted.invalid"] is None


@pytest.mark.parametrize("score,level", [(0.0, "low"), (0.2, "low"), (0.21, "mixed"), (0.5, "mixed"), (0.51, "ok")])
def test_level_thresholds_match_the_npm_package(score, level):
    assert cred1._level(score) == level


def test_search_is_sorted_least_credible_first_and_tolerates_bad_regex():
    hits = cred1.search("news")
    assert hits and all("news" in h["domain"] for h in hits)
    assert [h["score"] for h in hits] == sorted(h["score"] for h in hits)
    assert isinstance(cred1.search("[unclosed"), list)


def test_stats_counts_every_domain():
    s = cred1.stats()
    assert s["total_domains"] == len(DATA)
    assert sum(s["categories"].values()) == len(DATA)


def test_to_dataframe_has_one_row_per_domain():
    pd = pytest.importorskip("pandas")
    df = cred1.to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(DATA)
    assert list(df["score"]) == sorted(df["score"])
