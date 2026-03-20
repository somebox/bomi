"""JLCPCB Search and LCSC Detail API clients."""

import time

import requests

JLCPCB_SEARCH_URL = (
    "https://jlcpcb.com/api/overseas-pcb-order/v1/"
    "shoppingCart/smtGood/selectSmtComponentList"
)

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

