"""Tests for LLM datasheet analysis."""

import json
import pytest
from unittest.mock import patch, MagicMock

from jlcpcb_tool.analysis import analyze_part, _estimate_cost
from jlcpcb_tool.models import Part, PriceTier, Attribute


@pytest.fixture
def part_with_datasheet():
    return Part(
        lcsc_code="C8287",
        mfr_part="RC0402FR-0710KL",
        manufacturer="YAGEO",
        package="0402",
        description="10kΩ ±1% 1/16W 0402 Chip Resistor",
        stock=500000,
        datasheet_url="https://example.com/datasheet.pdf",
    )


@pytest.fixture
def part_no_datasheet():
    return Part(
        lcsc_code="C99999",
        mfr_part="TEST",
        manufacturer="Test",
    )


class TestAnalyzePart:
    def test_no_datasheet(self, tmp_db, part_no_datasheet):
        result = analyze_part(tmp_db, part_no_datasheet)
        assert "error" in result
        assert "No datasheet" in result["error"]

    def test_unknown_method(self, tmp_db, part_with_datasheet):
        result = analyze_part(tmp_db, part_with_datasheet, method="unknown")
        assert "error" in result

    @patch("jlcpcb_tool.analysis.get_secret")
    def test_no_api_key(self, mock_secret, tmp_db, part_with_datasheet):
        mock_secret.return_value = None
        result = analyze_part(tmp_db, part_with_datasheet, method="openrouter")
        assert "error" in result
        assert "not configured" in result["error"]

    @patch("jlcpcb_tool.analysis.requests.post")
    @patch("jlcpcb_tool.analysis.get_secret")
    def test_openrouter_success(self, mock_secret, mock_post,
                                 tmp_db, part_with_datasheet):
        mock_secret.return_value = "test-key"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Power rating: 1/16W"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Need part in DB for analysis save
        tmp_db.upsert_part(part_with_datasheet)

        result = analyze_part(tmp_db, part_with_datasheet, method="openrouter")
        assert result["response"] == "Power rating: 1/16W"
        assert result["method"] == "openrouter"
        assert result["cost_usd"] >= 0

        # Verify stored in DB
        analyses = tmp_db.get_analyses("C8287")
        assert len(analyses) == 1

    @patch("jlcpcb_tool.analysis.requests.post")
    @patch("jlcpcb_tool.analysis.get_secret")
    def test_llmlayer_success(self, mock_secret, mock_post,
                               tmp_db, part_with_datasheet):
        mock_secret.side_effect = lambda k: "test-key"

        # First call: LLMLayer extract
        extract_response = MagicMock()
        extract_response.json.return_value = {"text": "Extracted datasheet text..."}
        extract_response.raise_for_status = MagicMock()

        # Second call: OpenRouter completion
        completion_response = MagicMock()
        completion_response.json.return_value = {
            "choices": [{"message": {"content": "Analysis result"}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 100},
        }
        completion_response.raise_for_status = MagicMock()

        mock_post.side_effect = [extract_response, completion_response]

        tmp_db.upsert_part(part_with_datasheet)

        result = analyze_part(tmp_db, part_with_datasheet, method="llmlayer")
        assert result["response"] == "Analysis result"
        assert result["method"] == "llmlayer"
        assert result["extracted_text_length"] > 0


class TestEstimateCost:
    def test_zero_usage(self):
        assert _estimate_cost({}) == 0.0

    def test_with_tokens(self):
        cost = _estimate_cost({"prompt_tokens": 1000, "completion_tokens": 500})
        assert cost > 0
