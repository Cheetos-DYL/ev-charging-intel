"""Supabase (PostgREST) access. Writes use the service_role key (bypasses RLS)."""
from config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

TABLE = "ev_charging_articles"


def client():
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def existing_urls() -> set[str]:
    """All stored source_urls, for dedup.
    # ponytail: full column fetch, fine at <100k rows; switch to per-batch `in.()` filter when big"""
    rows = client().table(TABLE).select("source_url").execute().data or []
    return {r["source_url"] for r in rows}


def insert_article(row: dict) -> None:
    client().table(TABLE).upsert(row, on_conflict="source_url").execute()


def articles_for_week(iso_week: str) -> list[dict]:
    return (client().table(TABLE)
            .select("source_url,source_name,published_at,iso_week,region_group,country_code,"
                    "category_tags,importance_score,title_en,summary_bullets_en,strategic_implication_en")
            .eq("iso_week", iso_week)
            .order("importance_score", desc=True)
            .execute().data or [])


def unkeyed_articles() -> list[dict]:
    """Rows not yet topic-processed (topic_key IS NULL)."""
    return (client().table(TABLE)
            .select("id,title_en,published_at,region_group,mentioned_entities")
            .is_("topic_key", "null")
            .order("published_at", desc=True)
            .limit(500)
            .execute().data or [])


def set_topic_key(ids: list[str], topic_key: str) -> None:
    client().table(TABLE).update({"topic_key": topic_key}).in_("id", ids).execute()


def upsert_briefing(region_group: str, iso_week: str, briefing_html: str, article_count: int) -> None:
    client().table("weekly_briefings").upsert(
        {"region_group": region_group, "iso_week": iso_week,
         "briefing_html": briefing_html, "article_count": article_count},
        on_conflict="region_group,iso_week").execute()
