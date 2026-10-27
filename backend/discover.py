"""Node 1: discovery — Google News RSS (always) + Serper active search (if key)."""
import base64
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser
import httpx
from urllib.parse import parse_qs, parse_qsl

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

TRACKING_KEYS = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid", "igshid", "ref", "ref_src", "oc"}


def normalize_url(url: str) -> str:
    """Canonical form for dedup: lowercase host, drop tracking params + fragment."""
    p = urlparse(url.strip())
    query = [
        (k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS
    ]
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(query), ""))


def decode_gnews_target(url: str) -> str | None:
    """Google News RSS links are opaque redirects; the base64 blob usually hides the real URL."""
    m = re.search(r"/rss/articles/([^?]+)", url)
    if not m:
        return None
    blob = m.group(1)
    try:
        raw = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4))
    except Exception:
        return None
    m2 = re.search(rb"https?://[^\s\x00-\x1f\"'<>\\^`{|}]+", raw)
    if not m2:
        return None
    cand = m2.group(0).decode("ascii", "ignore")
    host = urlparse(cand).netloc
    return cand if host and "." in host else None


def resolve_source_url(url: str, timeout: float = 15.0) -> str | None:
    """Return the real article URL (or None if unresolvable)."""
    q = parse_qs(urlparse(url).query)
    if "url" in q:  # Bing apiclick redirector passes the target as ?url=
        return q["url"][0]
    if "news.google.com" not in url:
        return url
    dec = decode_gnews_target(url)
    if dec:
        return dec
    try:
        r = httpx.get(url, follow_redirects=True, timeout=timeout, headers={"User-Agent": UA})
        final = str(r.url)
        return None if "news.google.com" in final else final
    except Exception:
        return None


def news_rss_url(query: str, language: str, gl: str) -> str:
    """Bing News RSS search — real URLs, past-week window. (Google News RSS links no
    longer decode to targets upstream, 2025-10; qft interval:\"8\" = past week.
    Bing RSS silently returns 0 for parenthesized booleans — pass plain phrases.)"""
    from urllib.parse import quote
    setmkt = f"{language.split('-')[0]}-{gl}"
    return (
        "https://www.bing.com/news/search?q=" + quote(query)
        + f"&format=RSS&setmkt={setmkt}&qft=" + quote('interval:"8"')
    )


def _entry_dt(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def fetch_rss(search: dict, limit: int) -> list[dict]:
    """News-search RSS entries per phrase query, limited to the freshest `limit` items."""
    queries = search.get("bing_queries") or [search["query"]]
    out = []
    for q in queries:
        url = news_rss_url(q, search["language"], search["gl"])
        time.sleep(2)  # ponytail: Bing throttles rapid-fire RSS with silently-empty feeds; 2s spacing suffices at daily cadence
        try:
            resp = httpx.get(url, timeout=30, headers={"User-Agent": UA}, follow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            print(f"[discover] RSS fetch failed {search['region_group']}/{search['gl']}: {e}")
            continue
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:limit]:
            link = entry.get("link", "")
            if not link:
                continue
            out.append(dict(
                url=link,
                title=entry.get("title", "").strip(),
                source_name=(entry.get("source") or {}).get("title") or urlparse(link).netloc or search["gl"],
                published_at=_entry_dt(entry),
                region_group=search["region_group"],
                country_code=search["country_code"],
                language=search["language"],
                search_query_used=q,
                discovery_method="RSS",
            ))
        if len(out) >= limit:
            break
    return out[:limit]


def fetch_serper(search: dict, limit: int) -> list[dict]:
    """Active keyword search via Serper.dev (real URLs, past week). Skipped without key."""
    from config import SERPER_API_KEY
    if not SERPER_API_KEY:
        return []
    try:
        r = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": search["query"], "gl": search["gl"].lower(), "hl": search["hl"], "tbs": "qdr:w", "num": limit},
            timeout=30,
        )
        r.raise_for_status()
        results = r.json().get("organic", [])[:limit]
    except Exception as e:
        print(f"[discover] Serper failed {search['region_group']}: {e}")
        return []
    now = datetime.now(timezone.utc).isoformat()
    return [dict(
        url=item.get("link", ""),
        title=item.get("title", "").strip(),
        source_name=(urlparse(item.get("link", "")).netloc or "unknown"),
        published_at=now,
        region_group=search["region_group"],
        country_code=search["country_code"],
        language=search["language"],
        search_query_used=search["query"],
        discovery_method="ACTIVE_SEARCH",
    ) for item in results if item.get("link")]


def fetch_direct_feed(feed: dict, limit: int) -> list[dict]:
    """Direct publisher RSS — links are the real article URLs."""
    try:
        resp = httpx.get(feed["url"], timeout=30, headers={"User-Agent": UA}, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"[discover] direct feed failed {feed['url']}: {e}")
        return []
    parsed = feedparser.parse(resp.content)
    out = []
    for entry in parsed.entries[:limit]:
        link = entry.get("link", "")
        if not link:
            continue
        out.append(dict(
            url=link,
            title=entry.get("title", "").strip(),
            source_name=feed["source_name"],
            published_at=_entry_dt(entry),
            region_group=feed["region_group"],
            country_code=feed["country_code"],
            language=feed["language"],
            search_query_used=f"RSS:{feed['url']}",
            discovery_method="RSS",
        ))
    return out


def discover(sources: list[dict], limit: int = 5) -> list[dict]:
    """All discovery channels; URLs resolved + deduped in-run.
    Sources with 'query' = Google News RSS (+Serper); sources with 'url' = direct feeds."""
    seen, out = set(), []
    for src in sources:
        items = fetch_direct_feed(src, limit) if "url" in src else fetch_rss(src, limit) + fetch_serper(src, limit)
        for item in items:
            real = resolve_source_url(item["url"])
            if not real:
                continue
            key = normalize_url(real)
            if key in seen:
                continue
            seen.add(key)
            item["url"] = key  # store normalized (URL UNIQUE in DB)
            if "bing.com" in item["source_name"] or "google.com" in item["source_name"]:
                item["source_name"] = urlparse(real).netloc  # redirector host → real outlet
            out.append(item)
    return out
