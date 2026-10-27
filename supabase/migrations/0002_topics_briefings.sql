-- 0002: topic merging + per-market weekly briefings

-- same-topic grouping: rows sharing a topic_key cover the same underlying event
ALTER TABLE ev_charging_articles ADD COLUMN IF NOT EXISTS topic_key TEXT;
CREATE INDEX IF NOT EXISTS idx_articles_topic ON ev_charging_articles (topic_key);

-- generated weekly briefings, one row per market per ISO week
CREATE TABLE IF NOT EXISTS weekly_briefings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_group VARCHAR(20) NOT NULL,
    iso_week VARCHAR(10) NOT NULL,
    briefing_html TEXT NOT NULL,
    article_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (region_group, iso_week)
);

ALTER TABLE weekly_briefings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public read" ON weekly_briefings;
CREATE POLICY "public read" ON weekly_briefings FOR SELECT USING (true);
