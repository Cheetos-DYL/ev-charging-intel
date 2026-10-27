# EV Charging Market Intelligence Agent & Bilingual Archive

Implementation of [PRD.md](PRD.md) v2.1 on the PRD stack: Python pipeline → Supabase (PostgreSQL) → Next.js dashboard + weekly Telegram briefing.

## Layout

```
backend/     Python pipeline (discover → gatekeeper → translator → archive → weekly briefing)
frontend/    Next.js (App Router) dashboard — static export, deployable to GitHub Pages
supabase/    PostgreSQL schema (PRD §4) + public read-only RLS
.github/     ingest.yml (daily 06:00 UTC) · weekly.yml (Mon 07:00 UTC → Telegram)
```

## 1. Supabase

```bash
supabase link --project-ref <ref>          # inside this repo
printf 'y\n' | supabase db push            # applies supabase/migrations/
```

Fetch `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (backend writes) and the anon key (frontend reads) from Dashboard → API Keys. Writes run as `service_role` (bypasses RLS); the dashboard is public read-only.

## 2. Backend

```bash
cd backend
uv venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env   # fill in keys; source it or export before running
python test_pipeline.py   # self-check (offline)

python pipeline.py ingest --regions KR --limit 3 [--dry-run]   # Nodes 1-3
python pipeline.py topics                                      # merge same-topic articles
python pipeline.py briefings [--week 2026-W44] [--markets KR]   # per-market briefings -> DB
python pipeline.py weekly [--send]                             # Node 4 (default dry-run print)
```

- Discovery = Google News RSS per PRD §2 matrix (no key needed); Serper active search activates when `SERPER_API_KEY` is set. Google News redirect URLs stopped decoding upstream (2025-10) — unresolvable ones are skipped; `DIRECT_FEEDS` (real-URL publisher feeds, reused from ev-news-wiki) cover KR/TW/SG/AU_NZ/MENA/BR.
- Gatekeeper (Node 2) screens headline + first 2 paragraphs before any translation spend; drops are logged to `backend/logs/drops-YYYY-MM.jsonl`.
- LLM: opencode-go `deepseek-v4.1-flash` for gatekeeping + translation (`GATEKEEPER_MODEL` / `PROCESS_MODEL` knobs); `llm.py` sends the required `x-opencode-session` header.

## 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run build                # static export → out/
```

Deploy `out/` to GitHub Pages (or any static host). Single-page dashboard: market/tag/timeframe/search filters, article feed, side-by-side bilingual reader modal.

## 4. Automation secrets (GitHub repo)

`DEEPSEEK_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (+ optional `SERPER_API_KEY`); vars: `DASHBOARD_URL` (Telegram deep link), `GATEKEEPER_MODEL`, `PROCESS_MODEL`.
