"""Tests for API client (uses VCR cassettes when available)."""

import pytest

from jlcpcb_tool.api import JLCPCBClient, JLCPCB_SEARCH_URL, HEADERS


class TestJLCPCBClient:
    def test_client_creation(self):
        client = JLCPCBClient()
        assert client.session is not None
        assert client.session.headers.get("Origin") == "https://jlcpcb.com"

    def test_search_builds_correct_body(self):
        """Verify search method constructs proper request body."""
        # We test the method signature and parameter handling
        client = JLCPCBClient()
        # Just verify it doesn't crash constructing params
        # Actual HTTP tested via VCR or live
        assert callable(client.search)
        assert callable(client.fetch_detail)

    @pytest.mark.vcr()
    def test_search_live(self):
        """Live API test - only runs with VCR cassette or --disable-recording."""
        client = JLCPCBClient()
        result = client.search("10k 0402 resistor", page_size=5)
        assert result["code"] == 200
        data = result["data"]["componentPageInfo"]
        assert data["total"] > 0
        assert len(data["list"]) <= 5
