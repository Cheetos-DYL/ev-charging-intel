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
