"""
Tests for the PDF service — validation and text extraction.
"""

import pytest
from services.pdf_service import validate_pdf, extract_text_from_pdf
from fastapi import HTTPException


class TestValidatePdf:
    """Tests for the validate_pdf function."""

    def test_valid_pdf(self, sample_pdf_bytes):
        """A valid PDF should not raise any exception."""
        validate_pdf(sample_pdf_bytes, "application/pdf", "test.pdf")

    def test_invalid_content_type(self, sample_pdf_bytes):
        """Non-PDF content type should be rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(sample_pdf_bytes, "text/plain", "test.pdf")
        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail

    def test_invalid_extension(self, sample_pdf_bytes):
        """Non-.pdf extension should be rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(sample_pdf_bytes, "application/pdf", "test.txt")
        assert exc_info.value.status_code == 400
        assert "Invalid file extension" in exc_info.value.detail

    def test_file_too_large(self):
        """Files exceeding 20 MB should be rejected."""
        huge_bytes = b"%PDF-" + b"\x00" * (21 * 1024 * 1024)
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(huge_bytes, "application/pdf", "big.pdf")
        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail

    def test_bad_magic_bytes(self):
        """Files without PDF magic bytes should be rejected."""
        fake_bytes = b"NOT_A_PDF_FILE_CONTENT"
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(fake_bytes, "application/pdf", "fake.pdf")
        assert exc_info.value.status_code == 400
        assert "not appear to be a valid PDF" in exc_info.value.detail


class TestExtractTextFromPdf:
    """Tests for the extract_text_from_pdf function."""

    def test_extracts_text(self, sample_pdf_bytes):
        """Should extract text and return expected structure."""
        result = extract_text_from_pdf(sample_pdf_bytes)

        assert "text" in result
        assert "page_count" in result
        assert "word_count" in result
        assert "reading_time_minutes" in result
        assert "pages" in result

        assert result["page_count"] >= 1
        assert result["word_count"] > 0
        assert len(result["text"]) > 10

    def test_pages_structure(self, sample_pdf_bytes):
        """Each page should have the correct structure."""
        result = extract_text_from_pdf(sample_pdf_bytes)

        for page in result["pages"]:
            assert "page_number" in page
            assert "text" in page
            assert "char_count" in page
            assert isinstance(page["page_number"], int)

    def test_empty_pdf_raises_error(self):
        """A PDF with no extractable text should raise an error."""
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()  # blank page, no text
        empty_bytes = bytes(pdf.output())

        with pytest.raises(HTTPException) as exc_info:
            extract_text_from_pdf(empty_bytes)
        assert exc_info.value.status_code == 422
