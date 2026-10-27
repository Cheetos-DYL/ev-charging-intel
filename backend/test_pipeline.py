"""Runnable self-check for the pure logic. Run: python test_pipeline.py"""
import base64
from datetime import date

from agents import excerpt_of
from config import CATEGORY_TAGS, SEARCHES
from discover import decode_gnews_target, gnews_rss_url, normalize_url
from llm import parse_json
from pipeline import iso_week
from telegram import format_briefing, split_message


def test_normalize_url():
    assert normalize_url("HTTPS://Example.com/Article/?utm_source=x&fbclid=y&b=2&a=1") == "https://example.com/Article?b=2&a=1"
    assert normalize_url("https://example.com/a/") == normalize_url("https://example.com/a")


def test_decode_gnews_target():
    blob = base64.urlsafe_b64encode(b"\x08\x13\x22\x1ehttps://example.com/a/b?x=1").decode().rstrip("=")
    url = f"https://news.google.com/rss/articles/{blob}?oc=5"
    assert decode_gnews_target(url) == "https://example.com/a/b?x=1"
    assert decode_gnews_target("https://example.com/plain") is None


def test_gnews_urls():
    for s in SEARCHES:
        assert {"region_group", "country_code", "language", "hl", "gl", "ceid", "query"} <= set(s)
        u = gnews_rss_url(s)
        assert u.startswith("https://news.google.com/rss/search?q=") and f"ceid={s['ceid']}" in u
    assert {s["region_group"] for s in SEARCHES} == {"KR", "JP", "TW", "SG", "SEA", "AU_NZ", "MENA", "MX", "BR", "ZA"}
    assert len(CATEGORY_TAGS) == 7


def test_direct_feeds():
    from config import DIRECT_FEEDS, REGION_GROUPS
    for f in DIRECT_FEEDS:
        assert {"region_group", "country_code", "language", "url", "source_name"} <= set(f)
        assert f["url"].startswith("http") and f["region_group"] in REGION_GROUPS


def test_iso_week():
    assert iso_week(date(2026, 10, 26)) == "2026-W44"
    assert iso_week(date(2026, 1, 1)) == "2026-W01"


def test_split_message():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(100))
    chunks = split_message(text, limit=400)
    assert all(len(c) <= 400 for c in chunks)
    assert "\n".join(chunks) == text
    assert split_message("short", limit=400) == ["short"]


def test_excerpt_of():
    ex = excerpt_of("Title", "p1 line\n\np2 line\n\np3 line")
    assert ex.startswith("Title") and "p1 line" in ex and "p2 line" in ex and "p3" not in ex


def test_parse_json():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('noise {"b": 2} trailing') == {"b": 2}


def test_format_briefing():
    rows = {"https://src/1": {
        "source_url": "https://src/1", "region_group": "KR", "country_code": "KR",
        "category_tags": ["#Policy_Subsidy"], "importance_score": 4,
    }}
    text = format_briefing(
        week="2026-W44", date_range="Oct 26 – Nov 01, 2026", archived=3, filtered=7,
        clusters=[{"headline": "LTA <tender> opens", "synthesis": "SG CPO market & growth",
                   "importance": 4, "article_urls": ["https://src/1"]}],
        rows_by_url=rows,
    )
    assert "2026-W44" in text and "3 articles archived · 7 filtered" in text
    assert "https://src/1" in text and "LTA &lt;tender&gt;" in text and "&amp;" in text  # escaped
    assert "🇰🇷" in text
    text2 = format_briefing(week="2026-W44", date_range="x", archived=1, filtered=0,
                            clusters=[{"headline": "h", "synthesis": None, "importance": 3,
                                       "article_urls": ["https://src/1"]}], rows_by_url=rows)
    assert "None" not in text2  # null synthesis must not stringify


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all checks passed")
