"""
Integration tests for the API endpoints via FastAPI TestClient.
"""

import pytest
from tests.conftest import SAMPLE_TEXT, SHORT_TEXT


# ──────────────────────────────────────────────────────────────
# /api/upload
# ──────────────────────────────────────────────────────────────

class TestUploadEndpoint:
    """Tests for POST /api/upload."""

    def test_upload_valid_pdf(self, client, sample_pdf_bytes):
        """Uploading a valid PDF should succeed."""
        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "page_count" in data
        assert "word_count" in data
        assert data["filename"] == "test.pdf"

    def test_upload_invalid_type(self, client):
        """Uploading a non-PDF should return 400."""
        response = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"plain text content", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_wrong_extension(self, client, sample_pdf_bytes):
        """A PDF with wrong extension should return 400."""
        response = client.post(
            "/api/upload",
            files={"file": ("test.docx", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 400


# ──────────────────────────────────────────────────────────────
# /api/summarize
# ──────────────────────────────────────────────────────────────

class TestSummarizeEndpoint:
    """Tests for POST /api/summarize."""

    def test_summarize_valid_text(self, client):
        """Summarize endpoint should return a summary with metadata."""
        response = client.post(
            "/api/summarize",
            json={"text": SAMPLE_TEXT, "length": "short"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "method" in data
        assert "original_stats" in data

    def test_summarize_too_short(self, client):
        """Text shorter than 50 chars should return 400."""
        response = client.post(
            "/api/summarize",
            json={"text": SHORT_TEXT, "length": "medium"},
        )
        assert response.status_code == 400

    def test_summarize_default_length(self, client):
        """Omitting length should default to medium."""
        response = client.post(
            "/api/summarize",
            json={"text": SAMPLE_TEXT},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["length_setting"] == "medium"


# ──────────────────────────────────────────────────────────────
# /api/keywords
# ──────────────────────────────────────────────────────────────

class TestKeywordsEndpoint:
    """Tests for POST /api/keywords."""

    def test_keywords_valid_text(self, client):
        """Should return keywords with types."""
        response = client.post(
            "/api/keywords",
            json={"text": SAMPLE_TEXT, "top_n": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert "keywords" in data
        assert len(data["keywords"]) > 0
        assert "keyword" in data["keywords"][0]
        assert "type" in data["keywords"][0]

    def test_keywords_too_short(self, client):
        """Very short text should return 400."""
        response = client.post(
            "/api/keywords",
            json={"text": "Hi", "top_n": 5},
        )
        assert response.status_code == 400


# ──────────────────────────────────────────────────────────────
# /api/download
# ──────────────────────────────────────────────────────────────

class TestDownloadEndpoint:
    """Tests for POST /api/download."""

    def test_download_txt(self, client):
        """Download as TXT should return text/plain."""
        response = client.post(
            "/api/download",
            json={
                "summary": "This is a test summary.",
                "original_word_count": 100,
                "summary_word_count": 5,
                "format": "txt",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "PDF SUMMARY REPORT" in response.text

    def test_download_pdf(self, client):
        """Download as PDF should return application/pdf."""
        response = client.post(
            "/api/download",
            json={
                "summary": "This is a test summary.",
                "original_word_count": 100,
                "summary_word_count": 5,
                "format": "pdf",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:5] == b"%PDF-"

    def test_download_invalid_format(self, client):
        """Invalid format should return 400."""
        response = client.post(
            "/api/download",
            json={
                "summary": "Test.",
                "original_word_count": 10,
                "summary_word_count": 1,
                "format": "docx",
            },
        )
        assert response.status_code == 400


# ──────────────────────────────────────────────────────────────
# / health check
# ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    """Test the root health check endpoint."""

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PDF Summarizer API is running"
