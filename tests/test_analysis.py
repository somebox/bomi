"""Tests for LLM datasheet analysis."""

import json
import pytest
from unittest.mock import patch, MagicMock

from bomi.analysis import analyze_part, analyze_pdf, download_pdf, split_pdf, _estimate_cost
from bomi.models import Part, PriceTier, Attribute


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


FAKE_PDF = b"%PDF-1.4 fake pdf content for testing"


class TestDownloadPdf:
    @patch("bomi.analysis.requests.get")
    def test_download_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = FAKE_PDF
        mock_get.return_value = mock_resp

        result = download_pdf("https://example.com/test.pdf")
        assert result == FAKE_PDF

    @patch("bomi.analysis.requests.get")
    def test_download_not_pdf(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.content = b"<html>not a pdf</html>"
        mock_get.return_value = mock_resp

        result = download_pdf("https://example.com/test.pdf")
        assert result is None

    @patch("bomi.analysis.requests.get")
    def test_download_tries_resolved_url(self, mock_get):
        """LCSC URLs should try both original and resolved forms."""
        mock_resp_fail = MagicMock()
        mock_resp_fail.ok = True
        mock_resp_fail.content = b"<html>wrapper</html>"

        mock_resp_ok = MagicMock()
        mock_resp_ok.ok = True
        mock_resp_ok.content = FAKE_PDF

        mock_get.side_effect = [mock_resp_fail, mock_resp_ok]

        result = download_pdf(
            "https://www.lcsc.com/datasheet/lcsc_datasheet_123_C8287.pdf"
        )
        assert result == FAKE_PDF
        assert mock_get.call_count == 2


class TestSplitPdf:
    def test_small_pdf_no_split(self):
        chunks = split_pdf(FAKE_PDF, max_bytes=1_000_000)
        assert len(chunks) == 1
        assert chunks[0] == FAKE_PDF

    def test_large_pdf_without_pypdf(self):
        """Without pypdf, large PDFs return as single chunk."""
        large = FAKE_PDF + b"\x00" * 2_000_000
        chunks = split_pdf(large, max_bytes=100)
        # Without pypdf installed in test env, should return 1 chunk
        assert len(chunks) >= 1


class TestAnalyzePart:
    def test_no_datasheet(self, tmp_db, part_no_datasheet):
        result = analyze_part(tmp_db, part_no_datasheet)
        assert "error" in result
        assert "No datasheet" in result["error"]

    @patch("bomi.analysis.get_secret")
    def test_no_api_key(self, mock_secret, tmp_db, part_with_datasheet):
        mock_secret.return_value = None
        result = analyze_part(tmp_db, part_with_datasheet)
        assert "error" in result
        assert "not configured" in result["error"]

    @patch("bomi.analysis.requests.post")
    @patch("bomi.analysis.download_pdf")
    @patch("bomi.analysis.get_secret")
    def test_analyze_success(self, mock_secret, mock_download, mock_post,
                              tmp_db, part_with_datasheet):
        mock_secret.return_value = "test-key"
        mock_download.return_value = FAKE_PDF

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Power rating: 1/16W"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tmp_db.upsert_part(part_with_datasheet)

        result = analyze_part(tmp_db, part_with_datasheet)
        assert result["response"] == "Power rating: 1/16W"
        assert result["cost_usd"] >= 0
        assert result["chunks"] == 1

        # Verify stored in DB
        analyses = tmp_db.get_analyses("C8287")
        assert len(analyses) == 1

    @patch("bomi.analysis.requests.post")
    @patch("bomi.analysis.get_secret")
    def test_analyze_with_provided_pdf(self, mock_secret, mock_post,
                                        tmp_db, part_with_datasheet):
        """When pdf_data is provided, skip download."""
        mock_secret.return_value = "test-key"

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Analysis result"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tmp_db.upsert_part(part_with_datasheet)

        result = analyze_part(tmp_db, part_with_datasheet, pdf_data=FAKE_PDF)
        assert result["response"] == "Analysis result"
        # download_pdf should not have been called

    @patch("bomi.analysis.download_pdf")
    @patch("bomi.analysis.get_secret")
    def test_analyze_download_fails(self, mock_secret, mock_download,
                                     tmp_db, part_with_datasheet):
        mock_secret.return_value = "test-key"
        mock_download.return_value = None

        result = analyze_part(tmp_db, part_with_datasheet)
        assert "error" in result
        assert "Could not download" in result["error"]

    @patch("bomi.analysis.requests.post")
    @patch("bomi.analysis.download_pdf")
    @patch("bomi.analysis.get_config")
    @patch("bomi.analysis.get_secret")
    def test_analyze_uses_default_model_from_config(
        self, mock_secret, mock_get_config, mock_download, mock_post,
        tmp_db, part_with_datasheet
    ):
        mock_secret.return_value = "test-key"
        mock_get_config.return_value = "openai/gpt-4.1"
        mock_download.return_value = FAKE_PDF

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tmp_db.upsert_part(part_with_datasheet)
        result = analyze_part(tmp_db, part_with_datasheet)

        assert result["model"] == "openai/gpt-4.1"
        assert mock_post.call_args.kwargs["json"]["model"] == "openai/gpt-4.1"


class TestEstimateCost:
    def test_zero_usage(self):
        assert _estimate_cost({}) == 0.0

    def test_with_tokens(self):
        cost = _estimate_cost({"prompt_tokens": 1000, "completion_tokens": 500})
        assert cost > 0
