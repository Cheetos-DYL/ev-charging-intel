# Product Requirements Document (PRD): Global EV Charging Market Intelligence Agent & Bilingual Archive

**Document Version:** 2.1 (Final)
**Date:** October 2026
**Target Markets:** South Korea (KR), Japan (JP), Taiwan (TW), Singapore (SG), Southeast Asia (SEA), Australia & New Zealand (AU_NZ), Middle East & North Africa (MENA), Mexico (MX), Brazil (BR), South Africa (ZA)
**Delivery Channels:** Web Archive Dashboard (Full-Text Bilingual Repository) + Weekly Telegram Channel Briefing

---

## 1. Executive Summary & Objectives

### 1.1 Background

Global English-language media largely focuses on North American and European EV markets, leaving critical regulatory, infrastructure, and commercial developments in APAC, MENA, LATAM, and Africa under-reported. Conversely, scraping local-language media directly yields high noise, as local outlets frequently syndicate and translate foreign news (e.g., a South Korean newspaper reporting on US NEVI funding or Tesla layoffs in California).

### 1.2 Core Objectives

1. **Hybrid Native-Language Ingestion:** Proactively discover EV charging news in local languages using both automated RSS feeds and active keyword-driven Search Engine Result Page (SERP) queries across target regions.
2. **Strict Geo-Relevance Filtering:** Utilize an AI Gatekeeper agent to verify that the underlying event, policy, or business transaction physically or commercially pertains to the target local market, filtering out syndicated foreign news.
3. **Bilingual Full-Text Archiving:** Extract the clean, full-length original article and generate a complete, industry-accurate English translation. Store both side-by-side in a persistent database to prevent link rot and allow deep verification.
4. **Hybrid Delivery:** Provide a filterable Web Dashboard (by market, category tag, and date range) alongside an automated Weekly Executive Briefing pushed to a designated Telegram channel.

---

## 2. Target Markets & Multilingual Ingestion Matrix

The ingestion engine operates across distinct market groups, combining country/language-specific Google News RSS parameters (`gl`, `hl`, `ceid`) with active search API queries restricted to the past 7 days.

| Region Code | Target Market(s) | Languages | Active Search | Native Query Examples (Boolean) | Key Local Entities & Sources |
|---|---|---|---|---|---|
| KR | South Korea | Korean (ko) | Yes | `("전기차 충전" OR "충전 인프라" OR "급속충전기") AND ("환경부" OR "구축" OR "CPO" OR "로밍" OR "보조금")` | Ministry of Environment (ME), KEPCO, Electimes (전기신문), Energy Daily |
| JP | Japan | Japanese (ja) | Yes | `("EV充電" OR "急速充電器" OR "充電インフラ") AND ("設置" OR "補助金" OR "e-Mobility Power" OR "ENECHANGE")` | METI, e-Mobility Power (eMP), CHAdeMO, Response.jp, Nikkei |
| TW | Taiwan | Traditional Chinese (zh-TW) | Yes | `("電動車充電" OR "充電樁" OR "快充站") AND ("台電" OR "建置" OR "U-Power" OR "EVOASIS" OR "補助")` | Taipower (台電), U-Power, EVOASIS, Tailaka, U-Car, TechNews |
| SG | Singapore | English (en-SG), Simplified Chinese (zh-SG) | Yes | EN: `("EV charging" OR "EV charger") AND ("Singapore" OR "LTA" OR "HDB" OR "EVe") AND ("tender" OR "deployment" OR "roaming" OR "TR25")` / ZH: `("新加坡") AND ("电动车充电" OR "充电桩") AND ("陆交局" OR "建屋局")` | LTA, EVe, HDB, EMA, SP Mobility, Charge+, ComfortDelGro Engie, Straits Times, CNA, Lianhe Zaobao |
| SEA | Thailand, Indonesia, Vietnam, Malaysia | Thai (th), Indonesian (id), Vietnamese (vi), English (en) | Yes | TH: `"สถานีชาร์จ EV" OR "หัวชาร์จรถยนต์ไฟฟ้า"` / ID: `"SPKLU" OR "stasiun pengisian kendaraan listrik"` / VN: `"trạm sạc xe điện" OR "V-Green"` / MY: `"EV charging" AND ("Malaysia" OR "TNB" OR "PLANMalaysia")` | PLN (Indonesia), PEA/MEA/PTT (Thailand), V-Green/VinFast (Vietnam), TNB Electron/Gentari (Malaysia) |
| AU_NZ | Australia & New Zealand | English (en-AU, en-NZ) | Yes | `("EV charging" OR "fast charger") AND ("Australia" OR "New Zealand" OR "ARENA" OR "EECA" OR "NRMA" OR "Evie" OR "ChargeNet")` | ARENA, EECA, Evie Networks, Chargefox, Jolt, ChargeNet NZ, The Driven |
| MENA | UAE, Saudi Arabia (KSA), Qatar, Egypt, Israel | Arabic (ar), English (en) | Yes | AR: `("شحن السيارات الكهربائية" OR "محطات شحن") AND ("السعودية" OR "الإمارات" OR "DEWA" OR "EVIQ")` / EN: `"EV charging" AND ("UAE" OR "Saudi" OR "KSA" OR "DEWA" OR "TAQA" OR "EVIQ" OR "ADNOC")` | EVIQ (Saudi PIF/SEC JV), DEWA (Dubai), TAQA/ADNOC (Abu Dhabi), Zawya, Arab News |
| MX | Mexico | Spanish (es-MX) | Yes | `("infraestructura de carga" OR "electrolineras" OR "cargadores autos eléctricos") AND ("México" OR "CFE" OR "CRE")` | CFE (Comisión Federal de Electricidad), CRE, Vemo, Evergo, Cluster Industrial |
| BR | Brazil | Portuguese (pt-BR) | Yes | `("eletropostos" OR "infraestrutura de recarga" OR "carregadores carros eléctricos") AND ("Brasil" OR "ANEEL" OR "ABVE")` | ANEEL, ABVE, Tupinambá, Raízen Power, Zletric, CanalVE |
| ZA | South Africa | English (en-ZA) | Yes | `("EV charging" OR "electric vehicle charger") AND ("South Africa" OR "Eskom" OR "Zero Carbon Charge" OR "GridCars" OR "Rubicon")` | GridCars, Zero Carbon Charge (Off-grid), Rubicon, Eskom, Engineering News ZA |

---

## 3. System Architecture & AI Agent Workflow

The pipeline is structured into four sequential nodes to optimize LLM token costs and ensure data integrity.

### Node 1: Hybrid Discovery & Full-Text Extraction

- **Discovery:** Runs scheduled queries via Google News RSS feeds and Search APIs (Tavily / Serper.dev / DuckDuckGo) using the native-language matrix.
- **URL Deduplication:** Normalizes URLs (stripping UTM parameters) and checks against existing database entries.
- **Full-Text Scraping:** Extracts clean article body text in Markdown format using `trafilatura` (primary) or Jina Reader API / headless Playwright (fallback for dynamic/JS-heavy sites).

### Node 2: Geo-Relevance Gatekeeper Agent (Two-Stage Cost Filter)

To avoid paying translation tokens for irrelevant articles, a fast, cost-efficient model (e.g., Gemini 2.5 Flash or DeepSeek-V3) evaluates the **Headline + First 2 Paragraphs**.

**Inclusion Criteria (PASS):**
- The charging infrastructure rollout, government policy, grid upgrade, or commercial partnership physically occurs within the target market.
- A domestic company from the target market expands its charging business abroad, or a foreign player enters the target market (e.g., a Singapore CPO launching cross-border roaming in Malaysia triggers both SG and SEA tags).

**Exclusion Criteria (DROP):**
- **Foreign Syndication Noise:** A local media outlet reporting on events entirely in non-target markets (US, EU, Mainland China) without local market impact.
- **Non-Charging EV Noise:** General passenger EV car reviews, autonomous driving software updates, or battery mining news with zero mention of charging infrastructure, grid, or energy services.

### Node 3: Bilingual Translator & Taxonomy Tagger Agent

Articles that pass Node 2 are processed in full. The agent translates the complete article body into professional English and extracts structured metadata.

**Taxonomy Tags (`category_tags`):**
- `#CPO_Network` — Charge Point Operator rollouts, site host agreements, network expansion
- `#eMSP_Roaming` — App integrations, OCPI roaming, payment systems, pricing/tariffs
- `#Policy_Subsidy` — Government grants, mandates, technical regulations (e.g., TR25, AFIR equivalents), tenders
- `#Hardware_Tech` — Charger manufacturing, HPC (High-Power Charging), connector standards (CCS2, NACS, CHAdeMO), reliability
- `#Grid_Energy` — DNO/DSO grid connections, V2G/V2X, Smart Charging, BESS/Solar-integrated off-grid stations
- `#OEM_Initiative` — Automaker-led charging networks, bundled home/public charging offers
- `#Partnership_MnA` — Joint ventures, fundraising, M&A, commercial real estate / fleet deals

### Node 4: Weekly Synthesizer & Telegram Dispatcher

- Triggered weekly (e.g., every Monday at 08:00 local time).
- Queries all articles stored during the current ISO week (`YYYY-Www`).
- Clusters duplicate coverage of the same underlying event across multiple local outlets.
- Generates a concise, executive-level summary grouped by region, formatted in Telegram-compatible HTML, and dispatches it via the Telegram Bot API with deep links to the Web Dashboard.

---

## 4. Database Schema Specification

Designed for PostgreSQL (Supabase) or SQLite.

```sql
CREATE TABLE ev_charging_articles (
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

CREATE INDEX idx_articles_region_date ON ev_charging_articles (region_group, published_at DESC);
CREATE INDEX idx_articles_iso_week ON ev_charging_articles (iso_week);
CREATE INDEX idx_articles_tags ON ev_charging_articles USING GIN (category_tags);
```

---

## 5. AI Agent System Prompt Specification

```
You are a Principal Global EV Charging Market Intelligence Analyst.
Process the following scraped article from [TARGET_REGION / COUNTRY] into structured English intelligence.

### STEP 1: STRICT GEO-RELEVANCE GATEKEEPING

Determine if this article genuinely pertains to the EV charging ecosystem in [TARGET_REGION / COUNTRY].

- Set "is_relevant": false if:
  1. The article is syndicated/translated foreign news about non-target regions (e.g., US, Europe, or domestic Mainland China events) with no direct commercial or operational tie to [TARGET_REGION / COUNTRY].
  2. The article is solely about passenger EV vehicle launches, battery cell chemistry, or corporate stock prices without addressing charging infrastructure, CPOs, eMSPs, grid integration, or charging policy.

- Set "is_relevant": true if:
  1. The charging deployment, tender, policy, grid project, or partnership takes place within [TARGET_REGION / COUNTRY].
  2. An entity from [TARGET_REGION / COUNTRY] is expanding its charging operations internationally, or a foreign player is entering [TARGET_REGION / COUNTRY].

### STEP 2: FULL BILINGUAL TRANSLATION & STRUCTURED EXTRACTION

If relevant:
1. Translate the ENTIRE article body into professional, natural English (`full_text_en`). Do not summarize or truncate the full text translation.
2. Preserve all technical specifications (kW, MW, AC/DC, CCS1/CCS2/NACS/CHAdeMO/TR25), financial figures (keep original currency and add approximate USD equivalent in brackets), and proper nouns.
3. Enforce accurate EV industry terminology: CPO, eMSP, DNO/DSO, HPC, V2G, OCPP, ISO 15118, Roaming.

### OUTPUT FORMAT (STRICT JSON):

{
  "is_relevant": boolean,
  "drop_reason": "string or null",
  "region_group": "KR | JP | TW | SG | SEA | AU_NZ | MENA | MX | BR | ZA",
  "secondary_regions": ["string"],
  "country_code": "2-letter ISO code",
  "title_en": "Professional English headline",
  "summary_bullets_en": [
    "Key fact 1 (who, what, scale/numbers)",
    "Key fact 2 (timeline, location, technical spec)",
    "Key fact 3 (partner, regulatory context)"
  ],
  "strategic_implication_en": "1-sentence analysis of why this matters for the local CPO/eMSP/Charging market",
  "category_tags": ["#CPO_Network", "#eMSP_Roaming", "#Policy_Subsidy", "#Hardware_Tech", "#Grid_Energy", "#OEM_Initiative", "#Partnership_MnA"],
  "mentioned_entities": ["Entity1", "Entity2"],
  "importance_score": 1-5,
  "full_text_en": "Complete paragraph-by-paragraph English translation in Markdown"
}
```

---

## 6. Web Archive Dashboard & Telegram Delivery Requirements

### 6.1 Web Dashboard UI/UX Specifications

**Multi-Dimensional Filter Bar:**
- **Market Selector:** [All] [KR] [JP] [TW] [SG] [SEA] [AU_NZ] [MENA] [MX] [BR] [ZA]
- **Category Tag Filter:** Multi-select pills for the 7 value-chain tags.
- **Timeframe Filter:** ISO Week dropdown (2026-W44, 2026-W43, etc.), Last 7 Days, Last 30 Days, Custom Date Range.
- **Search Input:** Full-text search across English headlines, summaries, and `mentioned_entities`.

**Article Card Feed:**
- Displays: Country Flag + Region Badge, Category Tags, Importance Badge (★ 1–5), Discovery Method Badge (📡 RSS / 🔍 Active Search), Published Date, Source Name.
- Content: `title_en`, `summary_bullets_en`, and highlighted `strategic_implication_en`.

**Bilingual Side-by-Side Reader Modal:**
- Clicking any card opens a detail drawer/modal with three view modes:
  - **Side-by-Side View (Default on Desktop):** Left pane shows `full_text_original` (native language); Right pane shows `full_text_en` (complete English translation) for instant verification of numbers and nuances.
  - **English Only View**
  - **Original Text Only View**
- Includes a direct button to open the external `source_url`.

### 6.2 Weekly Telegram Briefing Format

**Trigger:** Automated weekly cron job.
**Constraint Handling:** Automatically splits messages if the weekly digest exceeds Telegram's 4,096-character limit per message.

**Template Structure:**
- Header with ISO Week, date range, and total articles processed vs. filtered.
- Grouped sections by Region (East Asia, Singapore & SEA, Oceania, MENA, LATAM & Africa).
- Top high-importance items (`importance_score >= 3`) featuring [Country | #Tags], bold English headline, 1-2 sentence synthesis, [Original Source] link, and [Bilingual Archive] deep link.

---

## 7. Recommended Tech Stack & Deployment

- **Scraper & Agent Backend:** Python 3.11+ (httpx, feedparser, trafilatura, pydantic, openai / google-genai SDK)
- **Search API:** Tavily API or Serper.dev (Google SERP API with gl/hl/tbs time-bound support)
- **Database:** Supabase (PostgreSQL) or local SQLite (synced via Litestream/Docker volume)
- **Web Frontend:** Next.js (App Router) or Astro + Tailwind CSS + Lucide Icons
- **Automation / Scheduler:** Linux systemd timer / cron (self-hosted) or GitHub Actions workflow
