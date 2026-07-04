"""JLCPCB Search API client, and OpenRouter model-pricing lookup."""

import time

import requests

JLCPCB_SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1/"
    "shoppingCart/smtGood/selectSmtComponentList"
)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://jlcpcb.com",
    "Referer": "https://jlcpcb.com/parts",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

THROTTLE_SECONDS = 1.5


class JLCPCBClient:
    """Client for the JLCPCB component search API."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self._last_request_time = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < THROTTLE_SECONDS:
            time.sleep(THROTTLE_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _sync_xsrf_token(self):
        """Forward XSRF-TOKEN cookie as X-XSRF-TOKEN header.

        The JLCPCB API sets an XSRF-TOKEN cookie on the first response
        and requires it back as a header on all subsequent requests,
        otherwise it returns 403 Forbidden.
        """
        xsrf = self.session.cookies.get("XSRF-TOKEN")
        if xsrf:
            self.session.headers["X-XSRF-TOKEN"] = xsrf

    def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 25,
        basic_only: bool = False,
        preferred_only: bool = False,
        component_type: str | None = None,
    ) -> dict:
        """Search JLCPCB catalog. Returns raw API response dict."""
        self._throttle()
        self._sync_xsrf_token()

        body = {
            "keyword": keyword,
            "currentPage": page,
            "pageSize": page_size,
        }
        if basic_only:
            body["componentLibraryType"] = "base"
        if preferred_only:
            body["preferredComponentFlag"] = True
        if component_type:
            body["componentType"] = component_type

        resp = self.session.post(JLCPCB_SEARCH_URL, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()


def fetch_openrouter_model_pricing() -> dict[str, dict[str, float]]:
    """Fetch current per-model pricing from OpenRouter's public model list.

    Returns a dict keyed by model id, each value ``{"prompt": <usd/token>,
    "completion": <usd/token>}``. This is a live lookup — no API key
    required — used as a fallback when a response doesn't include actual
    billed cost. Callers are expected to cache the result themselves since
    pricing changes infrequently but this endpoint lists every model.
    """
    resp = requests.get(OPENROUTER_MODELS_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    pricing: dict[str, dict[str, float]] = {}
    for entry in data.get("data", []):
        model_id = entry.get("id")
        prices = entry.get("pricing") or {}
        if not model_id:
            continue
        try:
            prompt = float(prices.get("prompt", 0) or 0)
            completion = float(prices.get("completion", 0) or 0)
        except (TypeError, ValueError):
            continue
        pricing[model_id] = {"prompt": prompt, "completion": completion}
    return pricing

