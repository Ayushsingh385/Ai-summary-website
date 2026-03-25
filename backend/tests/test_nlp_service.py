"""
Tests for the NLP service — summarization, keyword extraction, and text stats.
"""

import pytest
from services.nlp_service import (
    summarize_text,
    extract_keywords,
    compute_text_stats,
    _extract_keywords_frequency,
    _extractive_summarize,
    _get_sentences,
    _get_spacy_nlp,
)


# ──────────────────────────────────────────────────────────────
# Extractive Summarization Tests
# ──────────────────────────────────────────────────────────────

class TestExtractiveSummarize:
    """Tests for the extractive (fallback) summarizer."""

    def test_returns_expected_keys(self, sample_text):
        """Output should include summary, word counts, and method."""
        result = _extractive_summarize(sample_text, "medium")

        assert "summary" in result
        assert "summary_word_count" in result
        assert "original_word_count" in result
        assert "compression_ratio" in result
        assert "length_setting" in result
        assert result["method"] == "extractive"

    def test_short_summary_is_shorter(self, sample_text):
        """Short summary should have fewer words than medium."""
        short = _extractive_summarize(sample_text, "short")
        medium = _extractive_summarize(sample_text, "medium")
        assert short["summary_word_count"] <= medium["summary_word_count"]

    def test_compression_ratio_positive(self, sample_text):
        """Compression ratio should be positive for non-trivial text."""
        result = _extractive_summarize(sample_text, "short")
        assert result["compression_ratio"] > 0

    def test_handles_very_short_text(self):
        """Very short text with few sentences should return them all."""
        text = "This is sentence one. This is sentence two."
        result = _extractive_summarize(text, "medium")
        assert result["summary_word_count"] > 0


# ──────────────────────────────────────────────────────────────
# Keyword Extraction Tests
# ──────────────────────────────────────────────────────────────

class TestExtractKeywordsFrequency:
    """Tests for frequency-based keyword extraction."""

    def test_returns_list_of_dicts(self, sample_text):
        """Should return a list of keyword dicts."""
        result = _extract_keywords_frequency(sample_text, top_n=10)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "keyword" in result[0]
        assert "score" in result[0]

    def test_respects_top_n(self, sample_text):
        """Should return at most top_n keywords."""
        result = _extract_keywords_frequency(sample_text, top_n=5)
        assert len(result) <= 5

    def test_excludes_stop_words(self, sample_text):
        """Common stop words should not appear as keywords."""
        result = _extract_keywords_frequency(sample_text, top_n=50)
        keywords = [kw["keyword"] for kw in result]
        for stop in ["the", "and", "for", "that", "this", "with"]:
            assert stop not in keywords

    def test_sorted_by_frequency(self, sample_text):
        """Keywords should be sorted by score descending."""
        result = _extract_keywords_frequency(sample_text, top_n=10)
        scores = [kw["score"] for kw in result]
        assert scores == sorted(scores, reverse=True)


class TestExtractKeywordsNER:
    """Tests for the hybrid NER + frequency keyword extraction."""

    def test_returns_type_field(self, sample_text):
        """Each keyword should have a 'type' field."""
        result = extract_keywords(sample_text, top_n=10)
        for kw in result:
            assert "type" in kw
            assert "keyword" in kw
            assert "score" in kw

    def test_detects_named_entities(self, sample_text):
        """Should detect entities like 'Supreme Court', 'India', 'Article 21'."""
        nlp = _get_spacy_nlp()
        if nlp is None:
            pytest.skip("spaCy model not available")

        result = extract_keywords(sample_text, top_n=20)
        entity_types = {kw["type"] for kw in result}

        # At least one NER type should be present (not just FREQUENCY)
        non_freq = entity_types - {"FREQUENCY"}
        assert len(non_freq) > 0, f"Expected NER entities but only got: {entity_types}"

    def test_respects_top_n(self, sample_text):
        """Should return at most top_n results."""
        result = extract_keywords(sample_text, top_n=5)
        assert len(result) <= 5

    def test_fallback_on_empty_text(self):
        """Very short text should still return valid result."""
        result = extract_keywords("Python programming language is great", top_n=5)
        assert isinstance(result, list)


# ──────────────────────────────────────────────────────────────
# Text Stats Tests
# ──────────────────────────────────────────────────────────────

class TestComputeTextStats:
    """Tests for compute_text_stats."""

    def test_returns_expected_keys(self, sample_text):
        stats = compute_text_stats(sample_text)
        assert "word_count" in stats
        assert "char_count" in stats
        assert "sentence_count" in stats
        assert "reading_time_minutes" in stats

    def test_word_count_correct(self):
        text = "one two three four five"
        stats = compute_text_stats(text)
        assert stats["word_count"] == 5

    def test_reading_time_minimum_one(self):
        """Reading time should be at least 1 minute."""
        stats = compute_text_stats("short")
        assert stats["reading_time_minutes"] >= 1


# ──────────────────────────────────────────────────────────────
# Sentence Splitter Tests
# ──────────────────────────────────────────────────────────────

class TestGetSentences:
    """Tests for the _get_sentences helper."""

    def test_splits_on_period(self):
        text = "First sentence here. Second sentence there. Third one follows."
        sentences = _get_sentences(text)
        assert len(sentences) == 3

    def test_filters_short_fragments(self):
        """Fragments with 10 or fewer characters should be excluded."""
        text = "OK. This is a longer sentence that should be kept."
        sentences = _get_sentences(text)
        assert all(len(s) > 10 for s in sentences)

    def test_handles_multiple_whitespace(self):
        text = "First   sentence   here.    Second   sentence   there."
        sentences = _get_sentences(text)
        assert len(sentences) == 2


# ──────────────────────────────────────────────────────────────
# Summarize Text (public API) Tests
# ──────────────────────────────────────────────────────────────

class TestSummarizeText:
    """Tests for the public summarize_text function."""

    def test_returns_valid_structure(self, sample_text):
        """Should return a well-structured result dict."""
        result = summarize_text(sample_text, "medium")
        assert "summary" in result
        assert "method" in result
        assert result["method"] in ("abstractive", "extractive")

    def test_invalid_length_defaults_to_medium(self, sample_text):
        """Invalid length param should default to 'medium'."""
        result = summarize_text(sample_text, "invalid")
        assert result["length_setting"] == "medium"
