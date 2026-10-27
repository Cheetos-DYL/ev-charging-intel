"""Nodes 2+3: geo-relevance gatekeeper (cheap, excerpt-only) and full bilingual processor.

Two calls per article on purpose: Node 2 screens headline + first 2 paragraphs with a
small/cheap model so translation tokens are never spent on dropped articles (PRD §3).
"""
from config import CATEGORY_TAGS, GATEKEEPER_MODEL, PROCESS_MODEL
from llm import chat, parse_json

GATEKEEPER_PROMPT = """You are a Principal Global EV Charging Market Intelligence Analyst.
Determine if this article genuinely pertains to the EV charging ecosystem in {target}.

Set "is_relevant": false if:
1. The article is syndicated/translated foreign news about non-target regions (e.g., US, Europe, or domestic Mainland China events) with no direct commercial or operational tie to {target}.
2. The article is solely about passenger EV vehicle launches, battery cell chemistry, or corporate stock prices without addressing charging infrastructure, CPOs, eMSPs, grid integration, or charging policy.

Set "is_relevant": true if:
1. The charging deployment, tender, policy, grid project, or partnership takes place within {target}.
2. An entity from {target} is expanding its charging operations internationally, or a foreign player is entering {target}.

ARTICLE EXCERPT:
{excerpt}

OUTPUT FORMAT (STRICT JSON):
{{"is_relevant": boolean, "drop_reason": "string or null"}}"""

PROCESS_PROMPT = """You are a Principal Global EV Charging Market Intelligence Analyst.
Process the following scraped article from {target} into structured English intelligence.

1. Translate the ENTIRE article body into professional, natural English ("full_text_en"). Do not summarize or truncate the full text translation.
2. Preserve all technical specifications (kW, MW, AC/DC, CCS1/CCS2/NACS/CHAdeMO/TR25), financial figures (keep original currency and add approximate USD equivalent in brackets), and proper nouns.
3. Enforce accurate EV industry terminology: CPO, eMSP, DNO/DSO, HPC, V2G, OCPP, ISO 15118, Roaming.

ARTICLE:
{article}

OUTPUT FORMAT (STRICT JSON):
{{
  "region_group": "KR | JP | TW | SG | SEA | AU_NZ | MENA | MX | BR | ZA",
  "secondary_regions": ["string"],
  "country_code": "2-letter ISO code",
  "original_language": "language code of the article body",
  "title_en": "Professional English headline",
  "summary_bullets_en": [
    "Key fact 1 (who, what, scale/numbers)",
    "Key fact 2 (timeline, location, technical spec)",
    "Key fact 3 (partner, regulatory context)"
  ],
  "strategic_implication_en": "1-sentence analysis of why this matters for the local CPO/eMSP/Charging market",
  "category_tags": ["one or more of: {tags}"],
  "mentioned_entities": ["Entity1", "Entity2"],
  "importance_score": 1-5,
  "full_text_en": "Complete paragraph-by-paragraph English translation in Markdown"
}}"""


def excerpt_of(title: str, full_text: str, n_paragraphs: int = 2) -> str:
    paras = [p.strip() for p in full_text.split("\n") if p.strip()]
    return f"{title}\n\n" + "\n\n".join(paras[:n_paragraphs])


def gatekeeper(excerpt: str, target: str) -> dict:
    """Node 2: {is_relevant, drop_reason}."""
    raw = chat([{"role": "user", "content": GATEKEEPER_PROMPT.format(target=target, excerpt=excerpt[:4000])}],
               model=GATEKEEPER_MODEL, max_tokens=2000)
    out = parse_json(raw)
    return {"is_relevant": bool(out.get("is_relevant")), "drop_reason": out.get("drop_reason")}


def process_article(title_original: str, full_text_original: str, target: str) -> dict:
    """Node 3: full bilingual translation + structured metadata (strict fields)."""
    article = f"TITLE: {title_original}\n\n{full_text_original}"
    raw = chat([{"role": "user", "content": PROCESS_PROMPT.format(
        target=target, article=article[:60000], tags=", ".join(CATEGORY_TAGS))}],
        model=PROCESS_MODEL, max_tokens=8192)
    out = parse_json(raw)

    # validate taxonomy + score at the trust boundary (LLM output)
    tags = [t for t in out.get("category_tags", []) if t in CATEGORY_TAGS] or ["#CPO_Network"]
    try:
        importance = min(5, max(1, int(out.get("importance_score", 3))))
    except (TypeError, ValueError):
        importance = 3
    bullets = [str(b) for b in out.get("summary_bullets_en", [])][:3]

    return dict(
        region_group=out.get("region_group") or target,
        secondary_regions=[str(r) for r in out.get("secondary_regions", [])],
        country_code=str(out.get("country_code", ""))[:10],
        original_language=str(out.get("original_language", ""))[:10],
        title_en=str(out.get("title_en", "")),
        summary_bullets_en=bullets,
        strategic_implication_en=out.get("strategic_implication_en") or None,
        category_tags=tags,
        mentioned_entities=[str(e) for e in out.get("mentioned_entities", [])],
        importance_score=importance,
        full_text_en=str(out.get("full_text_en", "")),
    )
