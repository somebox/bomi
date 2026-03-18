#!/usr/bin/env python3
"""Test different OpenRouter models for datasheet analysis quality.

Uses CH224K (C970725) as the benchmark part. Downloads the PDF first,
then sends it as base64 to each model. Saves results for comparison.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

# Models to test
MODELS = [
    "z-ai/glm-5-turbo",
    "x-ai/grok-4.20-beta",
    "inception/mercury-2",
    "google/gemini-3.1-flash-lite-preview",
    "anthropic/claude-sonnet-4.6",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROMPT = """Provide a concise technical summary of this component. Include:
- Key specifications (voltage, current, temperature range)
- Complete pin descriptions with pin numbers
- Configuration options (CFG1/CFG2/CFG3 voltage settings)
- Typical application circuit component values
- Important design notes or limitations
Format as markdown. Be precise with pin numbers and specifications."""

# Test part: CH224K
PART_INFO = {
    "lcsc": "C970725",
    "mfr_part": "CH224K",
    "manufacturer": "WCH (Jiangsu Qin Heng)",
    "description": "USB PD 3.0 sink controller, 5/9/12/15/20V configurable",
}


def get_api_key():
    """Load OpenRouter API key from jlcpcb config."""
    key = os.environ.get("JLCPCB_OPENROUTER_API_KEY")
    if key:
        return key
    config_path = Path.home() / "Library" / "Application Support" / "jlcpcb" / "config.yaml"
    if config_path.exists():
        for line in config_path.read_text().splitlines():
            if "openrouter_api_key" in line:
                return line.split(":", 1)[1].strip().strip("\"'")
    print("ERROR: No OpenRouter API key found", file=sys.stderr)
    sys.exit(1)


def download_pdf(url: str) -> bytes | None:
    """Download a PDF, trying multiple URL forms."""
    import re
    urls = [url]
    m = re.search(r"lcsc\.com/datasheet/.*?(C\d+)\.pdf", url)
    if m:
        urls.append(f"https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{m.group(1)}.pdf")

    for u in urls:
        try:
            resp = requests.get(u, timeout=60, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            })
            if resp.ok and resp.content[:5] == b"%PDF-":
                return resp.content
        except requests.RequestException:
            continue
    return None


def analyze_with_model(api_key: str, model: str, pdf_b64: str) -> dict:
    """Send PDF to a model and return result."""
    text = (
        f"Part: {PART_INFO['lcsc']} ({PART_INFO['mfr_part']} by {PART_INFO['manufacturer']})\n"
        f"Description: {PART_INFO['description']}\n\n"
        f"{PROMPT}"
    )

    start = time.time()
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {
                            "url": f"data:application/pdf;base64,{pdf_b64}",
                        }},
                    ],
                }],
            },
            timeout=300,
        )
        elapsed = time.time() - start

        if not resp.ok:
            error_body = resp.text[:200]
            return {
                "model": model,
                "status": "error",
                "error": f"{resp.status_code}: {error_body}",
                "elapsed_s": round(elapsed, 1),
            }

        data = resp.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "model": model,
            "status": "ok",
            "response": choice,
            "elapsed_s": round(elapsed, 1),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
    except Exception as e:
        return {
            "model": model,
            "status": "error",
            "error": str(e),
            "elapsed_s": round(time.time() - start, 1),
        }


def main():
    output_dir = Path("test_model_results")
    output_dir.mkdir(exist_ok=True)

    api_key = get_api_key()

    # Step 1: Download PDF
    print("Downloading CH224K datasheet...", end="", flush=True)
    datasheet_url = "https://www.lcsc.com/datasheet/lcsc_datasheet_2403131354_WCH-Jiangsu-Qin-Heng-CH224K_C970725.pdf"
    pdf_data = download_pdf(datasheet_url)
    if not pdf_data:
        print(" FAILED - no PDF available")
        sys.exit(1)

    pdf_path = output_dir / "CH224K_C970725.pdf"
    pdf_path.write_bytes(pdf_data)
    print(f" {len(pdf_data) // 1024}KB")

    pdf_b64 = base64.b64encode(pdf_data).decode("ascii")

    # Step 2: Test each model
    results = []
    for model in MODELS:
        short = model.split("/")[-1]
        print(f"\nTesting {model}...", flush=True)

        result = analyze_with_model(api_key, model, pdf_b64)
        results.append(result)

        if result["status"] == "ok":
            # Save individual markdown
            md_path = output_dir / f"CH224K_{short}.md"
            md_path.write_text(
                f"# CH224K Summary — {model}\n\n"
                f"**Time:** {result['elapsed_s']}s | "
                f"**Tokens:** {result['total_tokens']} "
                f"({result['prompt_tokens']}+{result['completion_tokens']})\n\n"
                f"---\n\n"
                f"{result['response']}"
            )
            print(f"  OK: {result['elapsed_s']}s, {result['total_tokens']} tokens → {md_path}")
        else:
            print(f"  FAILED: {result['error']}")

    # Step 3: Print comparison table
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Model':<45} {'Status':<8} {'Time':>6} {'Tokens':>8}")
    print("-" * 70)
    for r in results:
        short = r["model"]
        status = r["status"]
        elapsed = f"{r['elapsed_s']}s"
        tokens = str(r.get("total_tokens", "-"))
        print(f"{short:<45} {status:<8} {elapsed:>6} {tokens:>8}")

    # Save raw results
    results_path = output_dir / "results.json"
    # Strip response text for JSON summary (too large)
    summary = []
    for r in results:
        s = {k: v for k, v in r.items() if k != "response"}
        if r["status"] == "ok":
            s["response_length"] = len(r.get("response", ""))
        summary.append(s)
    results_path.write_text(json.dumps(summary, indent=2))
    print(f"\nRaw results: {results_path}")


if __name__ == "__main__":
    main()
