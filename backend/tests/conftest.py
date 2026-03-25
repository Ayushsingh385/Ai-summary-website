"""
Shared pytest fixtures for the PDF Summarizer test suite.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


# ──────────────────────────────────────────────────────────────
# FastAPI test client
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Provide a FastAPI TestClient for integration tests."""
    return TestClient(app)


# ──────────────────────────────────────────────────────────────
# Sample text fixtures
# ──────────────────────────────────────────────────────────────

SAMPLE_TEXT = (
    "The Supreme Court of India delivered a landmark judgment on Article 21 "
    "of the Constitution. Justice Ramesh Kumar presided over the case involving "
    "the National Human Rights Commission and the State of Maharashtra. "
    "The petitioner argued that the right to life includes the right to live "
    "with dignity, citing several precedents from the High Court of Bombay. "
    "The Attorney General presented arguments on behalf of the Union of India. "
    "The case was filed under Section 32 of the Constitution and involved "
    "questions of fundamental rights, civil liberties, and due process of law. "
    "The judgment was delivered on 15 March 2024 and has significant implications "
    "for human rights jurisprudence in India. The bench also considered the "
    "International Covenant on Civil and Political Rights while arriving at "
    "its decision. The ruling affects approximately 50 million citizens."
)

SHORT_TEXT = "This is too short."


@pytest.fixture
def sample_text():
    """Return a realistic legal text for testing."""
    return SAMPLE_TEXT


@pytest.fixture
def short_text():
    """Return text that is too short for processing."""
    return SHORT_TEXT


# ──────────────────────────────────────────────────────────────
# Sample PDF fixture
# ──────────────────────────────────────────────────────────────

def _make_minimal_pdf(text: str = "Hello World. This is a test PDF document.") -> bytes:
    """Create a minimal valid PDF file in memory."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


@pytest.fixture
def sample_pdf_bytes():
    """Return bytes of a valid PDF containing sample text."""
    return _make_minimal_pdf(SAMPLE_TEXT)


@pytest.fixture
def minimal_pdf_bytes():
    """Return bytes of a minimal valid PDF."""
    return _make_minimal_pdf()
