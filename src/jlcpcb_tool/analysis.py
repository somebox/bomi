"""LLM datasheet analysis via OpenRouter and LLMLayer."""

import json
import re

import requests

from .config import get_secret
from .db import Database
from .models import Analysis, Part

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLMLAYER_URL = "https://api.llmlayer.com/v1"

DEFAULT_VISION_MODEL = "google/gemini-2.0-flash-001"
DEFAULT_TEXT_MODEL = "google/gemini-2.0-flash-001"

# LCSC datasheet wrapper URL pattern — resolves to direct PDF
_LCSC_DATASHEET_RE = re.compile(r"lcsc\.com/datasheet/.*?(C\d+)\.pdf")
_DIRECT_PDF_TEMPLATE = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{code}.pdf"


def _resolve_datasheet_url(url: str) -> str:
    """Resolve an LCSC datasheet wrapper URL to a direct PDF link.

    The JLCPCB API returns URLs like:
        https://www.lcsc.com/datasheet/lcsc_datasheet_..._C114581.pdf
    which serve an HTML wrapper page (not a PDF).  The actual PDF is at:
        https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/C114581.pdf
    """
    m = _LCSC_DATASHEET_RE.search(url)
    if m:
        return _DIRECT_PDF_TEMPLATE.format(code=m.group(1))
    return url


def analyze_part(
    db: Database,
    part: Part,
    method: str = "openrouter",
    prompt: str = "Summarize the key specifications from this datasheet.",
    model: str | None = None,
) -> dict:
    """Analyze a part's datasheet. Returns result dict."""
    if not part.datasheet_url:
        return {
            "error": "No datasheet URL available for this part.",
            "lcsc_code": part.lcsc_code,
        }

    if method == "openrouter":
        return _analyze_openrouter(db, part, prompt, model)
    elif method == "llmlayer":
        return _analyze_llmlayer(db, part, prompt, model)
    else:
        return {"error": f"Unknown method: {method}"}


def _analyze_openrouter(
    db: Database, part: Part, prompt: str, model: str | None
) -> dict:
    """Send datasheet PDF URL to OpenRouter vision model."""
    api_key = get_secret("openrouter_api_key")
    if not api_key:
        return {"error": "openrouter_api_key not configured (set in config.yaml or JLCPCB_OPENROUTER_API_KEY)"}

    model = model or DEFAULT_VISION_MODEL
    datasheet_url = _resolve_datasheet_url(part.datasheet_url)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Part: {part.lcsc_code} ({part.mfr_part} by {part.manufacturer})\n"
                        f"Description: {part.description}\n\n"
                        f"{prompt}"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": datasheet_url},
                },
            ],
        }
    ]

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    response_text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    cost = _estimate_cost(usage)

    analysis = Analysis(
        lcsc_code=part.lcsc_code,
        method="openrouter",
        model=model,
        prompt=prompt,
        response=response_text,
        cost_usd=cost,
    )
    analysis.id = db.save_analysis(analysis)

    return {
        "lcsc_code": part.lcsc_code,
        "method": "openrouter",
        "model": model,
        "prompt": prompt,
        "response": response_text,
        "cost_usd": cost,
    }


def _analyze_llmlayer(
    db: Database, part: Part, prompt: str, model: str | None
) -> dict:
    """Extract text via LLMLayer, then analyze with OpenRouter text model."""
    llmlayer_key = get_secret("llmlayer_api_key")
    openrouter_key = get_secret("openrouter_api_key")

    if not llmlayer_key:
        return {"error": "llmlayer_api_key not configured (set in config.yaml or JLCPCB_LLMLAYER_API_KEY)"}
    if not openrouter_key:
        return {"error": "openrouter_api_key not configured (set in config.yaml or JLCPCB_OPENROUTER_API_KEY)"}

    # Step 1: Extract text from PDF via LLMLayer
    extract_resp = requests.post(
        f"{LLMLAYER_URL}/extract",
        headers={
            "Authorization": f"Bearer {llmlayer_key}",
            "Content-Type": "application/json",
        },
        json={"url": _resolve_datasheet_url(part.datasheet_url), "output_format": "text"},
        timeout=120,
    )
    extract_resp.raise_for_status()
    extracted_text = extract_resp.json().get("text", "")

    if not extracted_text:
        return {"error": "LLMLayer returned no text from datasheet"}

    # Step 2: Send extracted text to OpenRouter text model
    model = model or DEFAULT_TEXT_MODEL
    messages = [
        {
            "role": "user",
            "content": (
                f"Part: {part.lcsc_code} ({part.mfr_part} by {part.manufacturer})\n"
                f"Description: {part.description}\n\n"
                f"Extracted datasheet text:\n{extracted_text[:50000]}\n\n"
                f"{prompt}"
            ),
        }
    ]

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    response_text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    cost = _estimate_cost(usage)

    analysis = Analysis(
        lcsc_code=part.lcsc_code,
        method="llmlayer",
        model=model,
        prompt=prompt,
        response=response_text,
        extracted_json=json.dumps({"extracted_text_length": len(extracted_text)}),
        cost_usd=cost,
    )
    analysis.id = db.save_analysis(analysis)

    return {
        "lcsc_code": part.lcsc_code,
        "method": "llmlayer",
        "model": model,
        "prompt": prompt,
        "response": response_text,
        "extracted_text_length": len(extracted_text),
        "cost_usd": cost,
    }


def _estimate_cost(usage: dict) -> float:
    """Estimate cost from usage data. Rough estimate."""
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    # Gemini Flash pricing approximation
    return (prompt_tokens * 0.075 + completion_tokens * 0.30) / 1_000_000
