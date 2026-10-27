-- PRD §4 schema, verbatim + read-only RLS for the public dashboard.
-- Writes go through the service_role key (bypasses RLS); frontend reads need public SELECT.

create table if not exists ev_charging_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 1. Provenance & Temporal Metadata
    source_url TEXT UNIQUE NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    discovery_method VARCHAR(50) NOT NULL,   -- 'RSS' or 'ACTIVE_SEARCH'
    search_query_used TEXT,                  -- Native keyword that surfaced the article
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    iso_week VARCHAR(10) NOT NULL,           -- Format: '2026-W44'

    -- 2. Geo & Taxonomy Classification
    region_group VARCHAR(20) NOT NULL,       -- 'KR','JP','TW','SG','SEA','AU_NZ','MENA','MX','BR','ZA'
    secondary_regions VARCHAR(20)[],         -- For cross-border news (e.g., ['SG', 'SEA'])
    country_code VARCHAR(10) NOT NULL,       -- ISO 3166-1 alpha-2 (e.g., 'KR', 'SG', 'TH', 'AE', 'BR')
    original_language VARCHAR(10) NOT NULL,  -- 'ko', 'ja', 'zh-TW', 'zh-SG', 'ar', 'pt', 'es', 'th', 'id', 'vi', 'en'
    category_tags TEXT[] NOT NULL,           -- Array of taxonomy tags
    mentioned_entities TEXT[],               -- Key companies/agencies (e.g., ['LTA', 'SP Mobility', 'EVIQ'])
    importance_score INTEGER CHECK (importance_score BETWEEN 1 AND 5),

    -- 3. Executive Summary & Insights
    title_original TEXT NOT NULL,
    title_en TEXT NOT NULL,
    summary_bullets_en TEXT[] NOT NULL,      -- 3 concise bullet points in English
    strategic_implication_en TEXT,           -- 1-sentence "So What?" business takeaway

    -- 4. Full-Text Bilingual Archive
    full_text_original TEXT NOT NULL,        -- Clean scraped native-language body (Markdown)
    full_text_en TEXT NOT NULL               -- Complete English translation of body (Markdown)
);

CREATE INDEX IF NOT EXISTS idx_articles_region_date ON ev_charging_articles (region_group, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_iso_week ON ev_charging_articles (iso_week);
CREATE INDEX IF NOT EXISTS idx_articles_tags ON ev_charging_articles USING GIN (category_tags);

-- Public read-only archive; all writes via service_role key only.
ALTER TABLE ev_charging_articles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "public read" ON ev_charging_articles;
CREATE POLICY "public read" ON ev_charging_articles FOR SELECT USING (true);
