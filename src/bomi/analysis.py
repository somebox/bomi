"""LLM datasheet analysis via OpenRouter.

Pipeline:
  1. download_pdf()  — fetch PDF bytes from LCSC or manufacturer URL
  2. split_pdf()     — split large PDFs into chunks (if needed)
  3. analyze_pdf()   — send PDF chunk(s) to OpenRouter via file content type
  4. analyze_part()  — orchestrates the above for a Part object

All analysis goes through OpenRouter using the `file` content type with
the file-parser plugin. This works with any model on OpenRouter.
"""

import base64
import json
import math
import re

import requests

from .config import get_config, get_secret
from .db import Database
from .models import Analysis, Part

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"

# Max PDF size (bytes) before splitting. ~1.5MB is safe for most models.
MAX_PDF_CHUNK_BYTES = 1_500_000

# LCSC datasheet wrapper URL pattern
_LCSC_DATASHEET_RE = re.compile(r"lcsc\.com/datasheet/.*?(C\d+)\.pdf")
_DIRECT_PDF_TEMPLATE = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{code}.pdf"

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------

def resolve_datasheet_url(url: str) -> str:
    """Resolve an LCSC datasheet wrapper URL to a direct PDF link.

    LCSC API returns wrapper URLs that serve HTML, not PDFs. The actual
    PDF is at wmsc.lcsc.com. Some of these work for direct download,
    others are JS-gated.
    """
    m = _LCSC_DATASHEET_RE.search(url)
    if m:
        return _DIRECT_PDF_TEMPLATE.format(code=m.group(1))
    return url


def download_pdf(url: str) -> bytes | None:
    """Download a PDF from a datasheet URL.

    Tries the original URL first (works for manufacturer-hosted PDFs and
    some LCSC URLs), then the resolved wmsc.lcsc.com URL as fallback.

    Returns PDF bytes, or None if download fails.
    """
    urls_to_try = [url]
    resolved = resolve_datasheet_url(url)
    if resolved != url:
        urls_to_try.append(resolved)

    for u in urls_to_try:
        try:
            resp = requests.get(
                u, timeout=60, allow_redirects=True,
                headers={"User-Agent": _USER_AGENT},
            )
            if resp.ok and resp.content[:5] == b"%PDF-":
                return resp.content
        except requests.RequestException:
            continue
    return None


# ---------------------------------------------------------------------------
# PDF splitting
# ---------------------------------------------------------------------------

def split_pdf(pdf_data: bytes, max_bytes: int = MAX_PDF_CHUNK_BYTES) -> list[bytes]:
    """Split a PDF into smaller chunks by page ranges.

    Uses PyPDF if available, otherwise returns the whole PDF as a single
    chunk (the caller handles the error if it's too large).
    """
    if len(pdf_data) <= max_bytes:
        return [pdf_data]

    try:
        from io import BytesIO
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        # No pypdf available — return as single chunk, let the API handle it
        return [pdf_data]

    reader = PdfReader(BytesIO(pdf_data))
    total_pages = len(reader.pages)

    if total_pages <= 1:
        return [pdf_data]

    # Estimate pages per chunk based on average page size
    avg_page_bytes = len(pdf_data) / total_pages
    pages_per_chunk = max(1, int(max_bytes / avg_page_bytes))

    chunks = []
    for start in range(0, total_pages, pages_per_chunk):
        end = min(start + pages_per_chunk, total_pages)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        buf = BytesIO()
        writer.write(buf)
        chunks.append(buf.getvalue())

    return chunks


# ---------------------------------------------------------------------------
# OpenRouter analysis
# ---------------------------------------------------------------------------

def _send_to_openrouter(
    api_key: str,
    model: str,
    text: str,
    pdf_data: bytes,
    filename: str,
    pdf_engine: str = "mistral-ocr",
) -> dict:
    """Send a single PDF to OpenRouter for analysis.

    Uses the `file` content type per OpenRouter's multimodal PDF docs.
    Works with any model — OpenRouter parses the PDF server-side when
    the model doesn't support files natively.
    """
    b64 = base64.b64encode(pdf_data).decode("ascii")

    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "file",
                    "file": {
                        "filename": filename,
                        "file_data": f"data:application/pdf;base64,{b64}",
                    },
                },
            ],
        }],
        "plugins": [{"id": "file-parser", "pdf": {"engine": pdf_engine}}],
    }

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def analyze_pdf(
    api_key: str,
    model: str,
    prompt: str,
    pdf_data: bytes,
    filename: str,
    pdf_engine: str = "mistral-ocr",
) -> dict:
    """Analyze a PDF, splitting into chunks if needed.

    For single-chunk PDFs, returns the response directly.
    For multi-chunk PDFs, analyzes each chunk separately then sends a
    final synthesis request to combine the results.

    Returns dict with 'response', 'cost_usd', 'model', 'chunks'.
    """
    chunks = split_pdf(pdf_data)
    total_cost = 0.0

    if len(chunks) == 1:
        data = _send_to_openrouter(api_key, model, prompt, chunks[0], filename, pdf_engine)
        usage = data.get("usage", {})
        return {
            "response": data["choices"][0]["message"]["content"],
            "cost_usd": _estimate_cost(usage),
            "model": model,
            "chunks": 1,
        }

    # Multi-chunk: analyze each chunk, then synthesize
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        chunk_prompt = (
            f"This is part {i + 1} of {len(chunks)} of a datasheet.\n\n"
            f"{prompt}\n\n"
            f"Focus on extracting all relevant information from this section. "
            f"If this section doesn't contain relevant info, say so briefly."
        )
        data = _send_to_openrouter(
            api_key, model, chunk_prompt, chunk,
            f"{filename}_part{i + 1}.pdf", pdf_engine,
        )
        usage = data.get("usage", {})
        total_cost += _estimate_cost(usage)
        chunk_summaries.append(data["choices"][0]["message"]["content"])

    # Synthesis pass — combine chunk results (text-only, no PDF)
    synthesis_prompt = (
        f"The following are summaries extracted from different sections of a "
        f"single datasheet, analyzed in {len(chunks)} parts.\n\n"
        f"Combine them into a single coherent technical summary. "
        f"Remove duplicates, resolve conflicts (later sections are more "
        f"specific), and produce the final markdown document.\n\n"
        f"Original request: {prompt}\n\n"
        + "\n\n---\n\n".join(
            f"### Part {i + 1} of {len(chunks)}:\n{s}"
            for i, s in enumerate(chunk_summaries)
        )
    )

    synth_resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": synthesis_prompt}],
        },
        timeout=300,
    )
    synth_resp.raise_for_status()
    synth_data = synth_resp.json()
    synth_usage = synth_data.get("usage", {})
    total_cost += _estimate_cost(synth_usage)

    return {
        "response": synth_data["choices"][0]["message"]["content"],
        "cost_usd": total_cost,
        "model": model,
        "chunks": len(chunks),
    }


# ---------------------------------------------------------------------------
# High-level: analyze a Part
# ---------------------------------------------------------------------------

def analyze_part(
    db: Database,
    part: Part,
    prompt: str = "Summarize the key specifications from this datasheet.",
    model: str | None = None,
    pdf_data: bytes | None = None,
    pdf_engine: str = "mistral-ocr",
) -> dict:
    """Analyze a part's datasheet. Downloads PDF if not provided.

    Args:
        db: Database instance for caching results.
        part: Part object with datasheet_url.
        prompt: Analysis prompt.
        model: Override model name.
        pdf_data: Pre-downloaded PDF bytes. If None, downloads automatically.
        pdf_engine: OpenRouter PDF parser engine ('mistral-ocr', 'pdf-text', 'native').

    Returns dict with 'response', 'cost_usd', 'model', etc.
    """
    if not part.datasheet_url and not pdf_data:
        return {"error": "No datasheet URL available for this part.", "lcsc_code": part.lcsc_code}

    api_key = get_secret("openrouter_api_key")
    if not api_key:
        from bomi.config import _global_config_path
        config_path = _global_config_path()
        return {"error": f"openrouter_api_key not configured (set in {config_path} or BOMI_OPENROUTER_API_KEY env var)"}

    model = model or get_config("default_model", DEFAULT_MODEL)

    # Step 1: Get PDF bytes
    if pdf_data is None:
        pdf_data = download_pdf(part.datasheet_url)
        if pdf_data is None:
            return {
                "error": f"Could not download datasheet from {part.datasheet_url}",
                "lcsc_code": part.lcsc_code,
            }

    # Step 2: Build prompt with part context
    full_prompt = (
        f"Part: {part.lcsc_code} ({part.mfr_part} by {part.manufacturer})\n"
        f"Description: {part.description}\n\n"
        f"{prompt}"
    )
    filename = f"{part.mfr_part}_datasheet.pdf".replace("/", "_").replace(" ", "_")

    # Step 3: Analyze (with chunking if needed)
    result = analyze_pdf(api_key, model, full_prompt, pdf_data, filename, pdf_engine)

    # Step 4: Cache in database
    analysis = Analysis(
        lcsc_code=part.lcsc_code,
        method="openrouter",
        model=model,
        prompt=prompt,
        response=result["response"],
        cost_usd=result.get("cost_usd", 0),
    )
    analysis.id = db.save_analysis(analysis)

    result["lcsc_code"] = part.lcsc_code
    result["prompt"] = prompt
    return result


def _estimate_cost(usage: dict) -> float:
    """Estimate cost from token usage. Rough approximation."""
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    return (prompt_tokens * 0.075 + completion_tokens * 0.30) / 1_000_000
