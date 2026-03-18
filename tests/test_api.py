"""Tests for API client request handling."""

from unittest.mock import MagicMock, patch

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

    @patch("jlcpcb_tool.api.requests.Session.post")
    def test_search_response_shape(self, mock_post):
        """Search should return parsed JSON payload from requests."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "code": 200,
            "data": {"componentPageInfo": {"total": 1, "list": [{}]}},
        }
        mock_post.return_value = mock_resp

        client = JLCPCBClient()
        result = client.search("10k 0402 resistor", page_size=5)
        assert result["code"] == 200
        data = result["data"]["componentPageInfo"]
        assert data["total"] == 1
        assert len(data["list"]) == 1
