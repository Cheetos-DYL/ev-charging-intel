"""Node 1: full-text extraction (trafilatura primary, Jina Reader fallback)."""
import httpx

from discover import UA


def extract_full_text(url: str, timeout: float = 30.0) -> str | None:
    """Clean article body in Markdown-ish text, or None if extraction fails."""
    try:
        resp = httpx.get(url, timeout=timeout, headers={"User-Agent": UA}, follow_redirects=True)
        resp.raise_for_status()
        import trafilatura
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=True, output_format="txt")
        if text and len(text.strip()) > 200:
            return text.strip()
    except Exception as e:
        print(f"[extract] trafilatura failed {url}: {e}")
    # fallback: Jina Reader (renders JS-heavy pages)
    try:
        r = httpx.get(f"https://r.jina.ai/{url}", timeout=60, headers={"User-Agent": UA})
        if r.status_code == 200 and len(r.text.strip()) > 200:
            return r.text.strip()
    except Exception as e:
        print(f"[extract] jina failed {url}: {e}")
    return None
