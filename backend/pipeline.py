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
from config import DIRECT_FEEDS, SEARCHES
from llm import chat, parse_json

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def iso_week(d: date | None = None) -> str:
    y, w, _ = (d or date.today()).isocalendar()
    return f"{y}-W{w:02d}"


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


def drops_this_week() -> int:
    """# ponytail: count from monthly JSONL logs; move drops into a DB table if ever needed for audit UI"""
    n = 0
    if not os.path.isdir(LOG_DIR):
        return 0
    for fn in os.listdir(LOG_DIR):
        if not fn.startswith("drops-"):
            continue
        for line in open(os.path.join(LOG_DIR, fn)):
            try:
                if json.loads(line).get("iso_week") == iso_week():
                    n += 1
            except json.JSONDecodeError:
                pass
    return n


def cmd_ingest(regions: set[str], limit: int, dry_run: bool) -> None:
    sources = [s for s in SEARCHES if not regions or s["region_group"] in regions]
    sources += [f for f in DIRECT_FEEDS if not regions or f["region_group"] in regions]
    if not sources:
        sys.exit(f"no markets match {sorted(regions)} (valid: {sorted({s['region_group'] for s in SEARCHES})})")

    items = discover.discover(sources, limit=limit)
    print(f"[ingest] discovered {len(items)} candidate URLs from {len(sources)} sources")

    existing = set() if dry_run else db.existing_urls()
    kept = [i for i in items if i["url"] not in existing]
    print(f"[ingest] {len(kept)} new after dedup ({len(items) - len(kept)} already stored)")

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
            iso_week=iso_week(),
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
    """One LLM call for the week: cluster duplicate coverage, executive synthesis (PRD Node 4)."""
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


def main() -> None:
    ap = argparse.ArgumentParser(description="EV charging intelligence pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ingest", help="Nodes 1-3: discover → gatekeep → translate → archive")
    a.add_argument("--regions", nargs="*", default=None, help="region groups (default: all)")
    a.add_argument("--limit", type=int, default=5, help="candidate URLs per search")
    a.add_argument("--dry-run", action="store_true")

    w = sub.add_parser("weekly", help="Node 4: weekly briefing → Telegram")
    w.add_argument("--send", action="store_true", help="actually send (default: dry-run print)")
    w.add_argument("--dry-run", action="store_true", help="skip LLM clustering; format raw rows only")

    args = ap.parse_args()
    if args.cmd == "ingest":
        cmd_ingest(set(args.regions or []), args.limit, args.dry_run)
    else:
        cmd_weekly(args.send, args.dry_run)


if __name__ == "__main__":
    main()
