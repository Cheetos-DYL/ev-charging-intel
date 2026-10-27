"""Pipeline CLI: ingest (Nodes 1-3) and weekly briefing (Node 4).

  python pipeline.py ingest [--regions KR JP] [--limit 5] [--dry-run]
  python pipeline.py weekly [--send] [--dry-run]
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

import agents
import db
import discover
import extract
import telegram
from config import DIRECT_FEEDS, REGION_GROUPS, SEARCHES
from llm import chat, parse_json

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def iso_week(d: date | None = None) -> str:
    y, w, _ = (d or date.today()).isocalendar()
    return f"{y}-W{w:02d}"


def within_days(published_at: str, days: int) -> bool:
    """True if ISO timestamp is within the last `days` days (days<=0 = no filter)."""
    if days <= 0:
        return True
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return True  # unparsable date → let it in rather than lose it
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return published >= cutoff


def log_drop(item: dict, reason: str) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    path = os.path.join(LOG_DIR, f"drops-{datetime.now():%Y-%m}.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "iso_week": iso_week(),
            "url": item["url"], "title": item.get("title", ""),
            "region_group": item.get("region_group", ""), "drop_reason": reason,
        }, ensure_ascii=False) + "\n")


def drops_this_week(region: str | None = None, week: str | None = None) -> int:
    n = 0
    target_week = week or iso_week()
    if not os.path.isdir(LOG_DIR):
        return 0
    for fn in os.listdir(LOG_DIR):
        if not fn.startswith("drops-"):
            continue
        for line in open(os.path.join(LOG_DIR, fn)):
            try:
                d = json.loads(line)
                if d.get("iso_week") == target_week and (region is None or d.get("region_group") == region):
                    n += 1
            except json.JSONDecodeError:
                pass
    return n


def logged_drop_urls() -> set[str]:
    """URLs already gatekeeper-dropped — skip reprocessing them.
    # ponytail: JSONL log doubles as dedup store; move drops to a DB table if ever needed for audit UI"""
    urls = set()
    if not os.path.isdir(LOG_DIR):
        return urls
    for fn in os.listdir(LOG_DIR):
        if fn.startswith("drops-"):
            for line in open(os.path.join(LOG_DIR, fn)):
                try:
                    urls.add(json.loads(line)["url"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return urls


def cmd_ingest(regions: set[str], limit: int, dry_run: bool, days: int = 7) -> None:
    sources = [s for s in SEARCHES if not regions or s["region_group"] in regions]
    sources += [f for f in DIRECT_FEEDS if not regions or f["region_group"] in regions]
    if not sources:
        sys.exit(f"no markets match {sorted(regions)} (valid: {sorted({s['region_group'] for s in SEARCHES})})")

    items = discover.discover(sources, limit=limit)
    print(f"[ingest] discovered {len(items)} candidate URLs from {len(sources)} sources")

    existing = set() if dry_run else db.existing_urls() | logged_drop_urls()
    kept = [i for i in items if i["url"] not in existing and within_days(i["published_at"], days)]
    print(f"[ingest] {len(kept)} new after dedup + {days}d window ({len(items) - len(kept)} dropped)")

    archived = dropped = failed = 0
    for item in kept:
        target = f"{item['region_group']} / {item['country_code']} ({item['language']})"
        text = extract.extract_full_text(item["url"])
        if not text:
            log_drop(item, "EXTRACTION_FAILED")
            failed += 1
            continue
        gate = agents.gatekeeper(agents.excerpt_of(item["title"], text), target)
        if not gate["is_relevant"]:
            log_drop(item, gate.get("drop_reason") or "NOT_GEO_RELEVANT")
            dropped += 1
            continue
        try:
            meta = agents.process_article(item["title"], text, target)
        except Exception as e:
            log_drop(item, f"PROCESS_FAILED: {e}")
            failed += 1
            continue
        row = dict(
            source_url=item["url"],
            source_name=item["source_name"],
            discovery_method=item["discovery_method"],
            search_query_used=item.get("search_query_used"),
            published_at=item["published_at"],
            iso_week=iso_week(datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).date()),
            title_original=item["title"],
            full_text_original=text,
            **{k: v for k, v in meta.items()},
        )
        if dry_run:
            print(f"[ingest][dry-run] would archive: {row['title_en'][:80]}")
        else:
            db.insert_article(row)
        archived += 1

    print(f"[ingest] done: {archived} archived, {dropped} dropped by gatekeeper, {failed} failed extraction/processing")


def synth_clusters(rows: list[dict]) -> list[dict]:
    """One LLM call: cluster duplicate coverage of the same event, executive synthesis (PRD Node 4)."""
    brief = [{k: r[k] for k in ("source_url", "source_name", "country_code", "region_group",
                                "title_en", "summary_bullets_en", "importance_score")} for r in rows]
    raw = chat([{"role": "user", "content":
        "You are a Principal Global EV Charging Market Intelligence Analyst. "
        "Cluster the week's articles: merge coverage of the SAME underlying event across outlets, "
        "keep separate events separate. For each cluster write one professional English headline and "
        "a 1-2 sentence executive synthesis (why it matters for CPO/eMSP/charging markets). "
        "Every article URL given MUST appear in exactly one cluster's article_urls.\n\n"
        "OUTPUT (STRICT JSON): {\"clusters\": [{\"headline\": \"...\", \"synthesis\": \"...\", "
        "\"importance\": 1-5, \"article_urls\": [\"...\"]}]}\n\n"
        "ARTICLES:\n" + json.dumps(brief, ensure_ascii=False)}],
        model=agents.PROCESS_MODEL, max_tokens=4096)
    clusters = parse_json(raw).get("clusters", [])
    covered = {u for c in clusters for u in c.get("article_urls", [])}
    for r in rows:  # anything the LLM dropped falls back to its own cluster
        if r["source_url"] not in covered:
            clusters.append(dict(headline=r["title_en"],
                                 synthesis=r.get("strategic_implication_en") or "",
                                 importance=r.get("importance_score") or 3,
                                 article_urls=[r["source_url"]]))
    return clusters


def cmd_weekly(send: bool, dry_run: bool) -> None:
    week = iso_week()
    rows = db.articles_for_week(week)
    if not rows:
        print(f"[weekly] no articles in {week}; nothing to send")
        return
    clusters = synth_clusters(rows) if not dry_run else [
        dict(headline=r["title_en"], synthesis=r.get("strategic_implication_en") or "",
             importance=r.get("importance_score") or 3, article_urls=[r["source_url"]])
        for r in rows
    ]
    d0 = datetime.strptime(week + "-1", "%G-W%V-%u").date()
    text = telegram.format_briefing(
        week=week,
        date_range=f"{d0:%b %d} – {(d0 + timedelta(days=6)):%b %d, %Y}",
        archived=len(rows),
        filtered=drops_this_week(),
        clusters=clusters,
        rows_by_url={r["source_url"]: r for r in rows},
    )
    for res in telegram.send_message(text, dry_run=not send):
        print(f"[weekly] send: {res}")


def topic_slug(text: str) -> str:
    """LLM topic label → safe slug for topic_key."""
    import re as _re
    s = _re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "topic"


def cmd_topics() -> None:
    """Merge same-topic articles: LLM-clusters unprocessed rows, sets shared topic_key.
    Every article gets a key (solo-<id8> for singletons) so unkeyed = unprocessed.
    # ponytail: clusters within one region per call; cross-region same-event merge if ever needed"""
    rows = db.unkeyed_articles()
    print(f"[topics] {len(rows)} unprocessed articles")
    by_region: dict[str, list[dict]] = {}
    for r in rows:
        by_region.setdefault(r["region_group"], []).append(r)
    for region, group in by_region.items():
        for start in range(0, len(group), 12):  # ponytail: 12/call — 25+ triggers empty completions upstream
            chunk = group[start:start + 12]
            brief = [{k: r[k] for k in ("id", "title_en", "published_at", "mentioned_entities")} for r in chunk]
            try:
                raw = chat([{"role": "user", "content":
                    "You are a market intelligence analyst. Group the articles into topics: articles covering the "
                    "SAME underlying event/topic belong in ONE cluster (e.g. multiple outlets reporting one tender). "
                    "Distinct events get their own clusters. Every article id MUST appear in exactly one cluster.\n\n"
                    "OUTPUT (STRICT JSON): {\"clusters\": [{\"topic_key\": \"short-english-slug\", \"article_ids\": [\"...\"]}]}\n\n"
                    "ARTICLES:\n" + json.dumps(brief, ensure_ascii=False)}],
                    model=agents.PROCESS_MODEL, max_tokens=4096)
                clusters = parse_json(raw).get("clusters", [])
            except Exception as e:
                print(f"[topics] {region} chunk {start}: clustering failed ({e}) → solo keys")
                clusters = []
            seen = set()
            merged = 0
            for cl in clusters:
                ids = [i for i in cl.get("article_ids", []) if isinstance(i, str)]
                key = topic_slug(str(cl.get("topic_key", "")))
                if len(ids) >= 2 and key and key != "topic":
                    db.set_topic_key(ids, key)
                    seen.update(ids)
                    merged += len(ids)
            for r in chunk:  # singletons + LLM stragglers
                if r["id"] not in seen:
                    db.set_topic_key([r["id"]], f"solo-{r['id'][:8]}")
        print(f"[topics] {region}: {len(group)} articles, merged into shared topics above")


def cmd_briefings(week: str, markets: set[str]) -> None:
    """Per-market weekly briefings → weekly_briefings table (topic clusters = merged coverage)."""
    rows = db.articles_for_week(week)
    d0 = datetime.strptime(week + "-1", "%G-W%V-%u").date()
    date_range = f"{d0:%b %d} – {(d0 + timedelta(days=6)):%b %d, %Y}"
    for region in REGION_GROUPS:
        if markets and region not in markets:
            continue
        rrows = [r for r in rows if r["region_group"] == region]
        if not rrows:
            continue
        try:
            clusters = synth_clusters(rrows) if len(rrows) > 1 else []
        except Exception as e:
            print(f"[briefings] {region} clustering failed ({e}) → unclustered items")
            clusters = []
        if not clusters:
            clusters = [
                dict(headline=r["title_en"], synthesis=r.get("strategic_implication_en") or "",
                     importance=r.get("importance_score") or 3, article_urls=[r["source_url"]])
                for r in rrows]
        text = telegram.format_briefing(
            week=week, date_range=date_range, archived=len(rrows),
            filtered=drops_this_week(region, week), clusters=clusters,
            rows_by_url={r["source_url"]: r for r in rrows},
        )
        db.upsert_briefing(region, week, text, len(rrows))
        print(f"[briefings] {region}: {len(rrows)} articles -> weekly_briefings")


def main() -> None:
    ap = argparse.ArgumentParser(description="EV charging intelligence pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ingest", help="Nodes 1-3: discover → gatekeep → translate → archive")
    a.add_argument("--regions", nargs="*", default=None, help="region groups (default: all)")
    a.add_argument("--limit", type=int, default=5, help="candidate URLs per search")
    a.add_argument("--days", type=int, default=7, help="only keep articles published within N days (0 = no filter)")
    a.add_argument("--dry-run", action="store_true")

    w = sub.add_parser("weekly", help="Node 4: weekly briefing → Telegram")
    w.add_argument("--send", action="store_true", help="actually send (default: dry-run print)")
    w.add_argument("--dry-run", action="store_true", help="skip LLM clustering; format raw rows only")

    t = sub.add_parser("topics", help="merge same-topic articles (sets topic_key)")

    b = sub.add_parser("briefings", help="per-market weekly briefings -> weekly_briefings table")
    b.add_argument("--week", default=iso_week(), help="ISO week, e.g. 2026-W44 (default: current)")
    b.add_argument("--markets", nargs="*", default=None, help="region groups (default: all)")

    args = ap.parse_args()
    if args.cmd == "ingest":
        cmd_ingest(set(args.regions or []), args.limit, args.dry_run, args.days)
    elif args.cmd == "weekly":
        cmd_weekly(args.send, args.dry_run)
    elif args.cmd == "topics":
        cmd_topics()
    else:
        cmd_briefings(args.week, set(args.markets or []))


if __name__ == "__main__":
    main()
