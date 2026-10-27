"""Node 4: weekly briefing formatting + Telegram dispatch (PRD §6.2)."""
import html
import os

import httpx

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")

# PRD §6.2 grouping
SECTIONS = {
    "East Asia": ["KR", "JP", "TW"],
    "Singapore & SEA": ["SG", "SEA"],
    "Oceania": ["AU_NZ"],
    "MENA": ["MENA"],
    "LATAM & Africa": ["MX", "BR", "ZA"],
}
SECTION_ICONS = {"East Asia": "🌏", "Singapore & SEA": "🌊", "Oceania": "🏝️", "MENA": "🏜️", "LATAM & Africa": "🌎"}
FLAG = {"KR": "🇰🇷", "JP": "🇯🇵", "TW": "🇹🇼", "SG": "🇸🇬", "TH": "🇹🇭", "ID": "🇮🇩", "VN": "🇻🇳",
        "MY": "🇲🇾", "AU": "🇦🇺", "NZ": "🇳🇿", "AE": "🇦🇪", "SA": "🇸🇦", "QA": "🇶🇦", "EG": "🇪🇬",
        "IL": "🇮🇱", "MX": "🇲🇽", "BR": "🇧🇷", "ZA": "🇿🇦"}


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Telegram caps messages at 4096 chars; split on line boundaries."""
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # pathological single line
            chunks.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks


def format_briefing(week: str, date_range: str, archived: int, filtered: int,
                    clusters: list[dict], rows_by_url: dict[str, dict]) -> str:
    """clusters: [{headline, synthesis, importance, article_urls:[source_url,...]}]"""
    lines = [
        f"<b>EV Charging Weekly Briefing — {week}</b>",
        f"{date_range} | {archived} articles archived · {filtered} filtered",
    ]
    for section, regions in SECTIONS.items():
        block = []
        for cl in clusters:
            urls = [u for u in cl.get("article_urls", []) if u in rows_by_url]
            rows = [rows_by_url[u] for u in urls]
            if not rows or not any(r["region_group"] in regions for r in rows):
                continue
            rep = max(rows, key=lambda r: r.get("importance_score") or 0)
            flags = " ".join(FLAG.get(r["country_code"], "🌐") for r in rows[:3])
            tags = " ".join(sorted({t for r in rows for t in (r.get("category_tags") or [])}))
            stars = "★" * int(rep.get("importance_score") or 0)
            block.append(
                f"\n<b>{flags} {rep['region_group']} | {tags} {stars}</b>\n"
                f"{html.escape(cl['headline'])}\n{html.escape(cl.get('synthesis') or '')}\n"
                f'<a href="{urls[0]}">Original Source</a>'
                + (f' · <a href="{DASHBOARD_URL}">Bilingual Archive</a>' if DASHBOARD_URL else "")
            )
        if block:
            lines.append(f"\n{SECTION_ICONS.get(section, '')} <b>{section}</b>" + "".join(block))
    return "\n".join(lines)


def send_message(text: str, token: str | None = None, chat_id: str | None = None,
                 dry_run: bool = False) -> list[dict]:
    token = token or TELEGRAM_BOT_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID
    chunks = split_message(text)
    if dry_run:
        return [{"ok": True, "dry_run": True, "text": c} for c in chunks]
    if not (token and chat_id):
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set")
    results = []
    for c in chunks:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": c, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=30,
        )
        results.append({"ok": r.is_success, "status": r.status_code, "body": r.text[:200]})
        if not r.is_success:
            break
    return results
