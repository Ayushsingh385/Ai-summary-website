"""
NLP Service — Summarization, keyword extraction, and text analysis.

Primary:  Abstractive summarization via Hugging Face facebook/bart-large-cnn.
Fallback: Statistical extractive summarization (sentence scoring) if the model
          cannot be loaded (offline, low memory, etc.).

Keywords: spaCy Named Entity Recognition (NER) + frequency-based extraction.
"""

import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# BART Pipeline (lazy-loaded singleton)
# ──────────────────────────────────────────────────────────────

_bart_pipeline = None
_bart_load_attempted = False


def _get_bart_pipeline():
    """Load the BART summarization pipeline once, on first call."""
    global _bart_pipeline, _bart_load_attempted

    if _bart_load_attempted:
        return _bart_pipeline  # May be None if loading failed earlier

    _bart_load_attempted = True
    try:
        from transformers import pipeline as hf_pipeline
        logger.info("Loading facebook/bart-large-cnn model (first request may take a minute)...")
        _bart_pipeline = hf_pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=-1,  # CPU
        )
        logger.info("BART model loaded successfully.")
    except Exception as exc:
        logger.warning("Could not load BART model — falling back to extractive: %s", exc)
        _bart_pipeline = None

    return _bart_pipeline


# ──────────────────────────────────────────────────────────────
# spaCy NLP model (lazy-loaded singleton)
# ──────────────────────────────────────────────────────────────

_spacy_nlp = None
_spacy_load_attempted = False


def _get_spacy_nlp():
    """Load the spaCy NLP model once, on first call."""
    global _spacy_nlp, _spacy_load_attempted

    if _spacy_load_attempted:
        return _spacy_nlp

    _spacy_load_attempted = True
    try:
        import spacy
        _spacy_nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy en_core_web_sm model loaded successfully.")
    except Exception as exc:
        logger.warning("Could not load spaCy model — falling back to frequency: %s", exc)
        _spacy_nlp = None

    return _spacy_nlp


# ──────────────────────────────────────────────────────────────
# Summary length presets
# ──────────────────────────────────────────────────────────────

# BART length params  (max_length, min_length)
BART_LENGTHS = {
    "short":  (80,  30),
    "medium": (200, 80),
    "long":   (400, 150),
}

# Extractive fallback: target sentence count
EXTRACTIVE_LENGTHS = {
    "short":  3,
    "medium": 7,
    "long":   15,
}

# BART handles at most ~1024 tokens.  We use a conservative character
# limit (~3 000 chars ≈ 750 tokens) per chunk to stay safely within bounds.
BART_CHUNK_CHARS = 3000

# Entity types to keep from spaCy NER
RELEVANT_ENTITY_TYPES = {
    "PERSON", "ORG", "GPE", "LOC", "LAW", "DATE", "EVENT",
    "NORP", "FAC", "PRODUCT", "WORK_OF_ART", "MONEY",
}


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def summarize_text(text: str, length: str = "medium") -> dict:
    """
    Summarize *text* using BART (abstractive) with an automatic fallback
    to extractive summarization if the model is unavailable.
    """
    if length not in BART_LENGTHS:
        length = "medium"

    pipe = _get_bart_pipeline()

    if pipe is not None:
        result = _bart_summarize(pipe, text, length)
    else:
        result = _extractive_summarize(text, length)

    return result


# ──────────────────────────────────────────────────────────────
# BART abstractive summarization
# ──────────────────────────────────────────────────────────────

def _bart_summarize(pipe, text: str, length: str) -> dict:
    """Run BART abstractive summarization, chunking if needed."""
    max_len, min_len = BART_LENGTHS[length]

    chunks = _split_into_chunks(text, BART_CHUNK_CHARS)
    logger.info("Summarising %d chunk(s) with BART [%s]", len(chunks), length)

    partial_summaries = []
    for i, chunk in enumerate(chunks):
        # Ensure min_len doesn't exceed the chunk word count
        chunk_words = len(chunk.split())
        effective_min = min(min_len, max(10, chunk_words // 3))
        effective_max = min(max_len, max(20, chunk_words))

        if effective_min >= effective_max:
            effective_min = max(10, effective_max - 10)

        try:
            out = pipe(
                chunk,
                max_length=effective_max,
                min_length=effective_min,
                do_sample=False,
                truncation=True,
            )
            partial_summaries.append(out[0]["summary_text"])
        except Exception as exc:
            logger.warning("BART failed on chunk %d, using raw chunk: %s", i, exc)
            partial_summaries.append(chunk[:max_len * 5])  # rough char approx

    combined_summary = " ".join(partial_summaries)

    # If we had many chunks, the combined summary can itself be long.
    # Do a second-pass summarization on the combined result.
    if len(chunks) > 1 and len(combined_summary.split()) > max_len * 1.5:
        try:
            second_pass = pipe(
                combined_summary,
                max_length=max_len,
                min_length=min_len,
                do_sample=False,
                truncation=True,
            )
            combined_summary = second_pass[0]["summary_text"]
        except Exception:
            pass  # Keep the first-pass combined summary

    original_word_count = len(text.split())
    summary_word_count = len(combined_summary.split())
    compression = round(
        (1 - summary_word_count / max(original_word_count, 1)) * 100, 1
    )

    return {
        "summary": combined_summary,
        "summary_word_count": summary_word_count,
        "original_word_count": original_word_count,
        "compression_ratio": compression,
        "length_setting": length,
        "method": "abstractive",
    }


def _split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of roughly *max_chars*, breaking at sentence boundaries."""
    sentences = _get_sentences(text)

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for sent in sentences:
        if current_len + len(sent) > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_len = 0
        current_chunk.append(sent)
        current_len += len(sent)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks if chunks else [text]


# ──────────────────────────────────────────────────────────────
# Extractive summarization (fallback)
# ──────────────────────────────────────────────────────────────

def _extractive_summarize(text: str, length: str) -> dict:
    """
    Generate an extractive summary by scoring sentences on word frequency.
    Used as a fallback when BART is unavailable.
    """
    target_sentences = EXTRACTIVE_LENGTHS.get(length, 7)
    sentences = _get_sentences(text)

    if len(sentences) <= target_sentences:
        combined_summary = " ".join(sentences)
    else:
        words = _extract_keywords_frequency(text, top_n=100)
        word_scores = {w["keyword"]: w["score"] for w in words}

        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = 0
            s_words = [re.sub(r"\W+", "", w.lower()) for w in sentence.split()]
            for word in s_words:
                if word in word_scores:
                    score += word_scores[word]

            position_boost = 1.0 if i > 3 else 1.5
            normalized_score = (score / (len(s_words) + 1)) * position_boost
            sentence_scores.append((normalized_score, i, sentence))

        sentence_scores.sort(key=lambda x: x[0], reverse=True)
        top_sentences = sentence_scores[:target_sentences]
        top_sentences.sort(key=lambda x: x[1])
        combined_summary = " ".join([s[2] for s in top_sentences])

    original_word_count = len(text.split())
    summary_word_count = len(combined_summary.split())
    compression = round(
        (1 - summary_word_count / max(original_word_count, 1)) * 100, 1
    )

    return {
        "summary": combined_summary,
        "summary_word_count": summary_word_count,
        "original_word_count": original_word_count,
        "compression_ratio": compression,
        "length_setting": length,
        "method": "extractive",
    }


# ──────────────────────────────────────────────────────────────
# Keyword extraction — spaCy NER + frequency hybrid
# ──────────────────────────────────────────────────────────────

def extract_keywords(text: str, top_n: int = 15) -> list[dict]:
    """
    Extract keywords using spaCy NER (primary) combined with frequency
    analysis.  Falls back to pure frequency if spaCy is unavailable.

    Returns a list of dicts:
        {"keyword": str, "score": int, "type": "PERSON"|"ORG"|...|"FREQUENCY"}
    """
    nlp = _get_spacy_nlp()

    if nlp is not None:
        return _extract_keywords_ner(nlp, text, top_n)

    # Fallback: pure frequency (adds "FREQUENCY" type for consistency)
    freq_keywords = _extract_keywords_frequency(text, top_n)
    for kw in freq_keywords:
        kw["type"] = "FREQUENCY"
    return freq_keywords


def _extract_keywords_ner(nlp, text: str, top_n: int = 15) -> list[dict]:
    """
    Hybrid keyword extraction:
      1. Run spaCy NER to find named entities.
      2. Run frequency analysis for non-entity important words.
      3. Merge and deduplicate, NER entities ranked first.
    """
    # ── Step 1: NER entities ──────────────────────────────────
    # spaCy has a max length; process in chunks if needed
    max_chars = 100_000
    if len(text) > max_chars:
        doc = nlp(text[:max_chars])
    else:
        doc = nlp(text)

    entity_counts: Counter = Counter()
    entity_labels: dict[str, str] = {}

    for ent in doc.ents:
        if ent.label_ not in RELEVANT_ENTITY_TYPES:
            continue
        # Normalise whitespace in entity text
        clean_text = " ".join(ent.text.split()).strip()
        if len(clean_text) < 2:
            continue
        entity_counts[clean_text] += 1
        entity_labels[clean_text] = ent.label_

    # Sort entities by frequency
    ner_keywords = [
        {"keyword": ent, "score": count, "type": entity_labels[ent]}
        for ent, count in entity_counts.most_common(top_n)
    ]

    # ── Step 2: Frequency keywords ────────────────────────────
    remaining_slots = max(0, top_n - len(ner_keywords))
    if remaining_slots > 0:
        freq_keywords = _extract_keywords_frequency(text, top_n=remaining_slots + 10)

        # Remove any frequency keywords that overlap with NER entities
        ner_lower = {kw["keyword"].lower() for kw in ner_keywords}
        for fkw in freq_keywords:
            if len(ner_keywords) >= top_n:
                break
            if fkw["keyword"].lower() not in ner_lower:
                fkw["type"] = "FREQUENCY"
                ner_keywords.append(fkw)

    return ner_keywords[:top_n]


# ──────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────

def _get_sentences(text: str) -> list[str]:
    """Split text into sentences using simple regex."""
    text = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _extract_keywords_frequency(text: str, top_n: int = 15) -> list[dict]:
    """Keyword extraction using word frequency analysis."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "this", "that", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does",
        "did", "will", "would", "could", "should", "may", "might", "shall",
        "can", "not", "no", "nor", "so", "if", "then", "than", "too", "very",
        "just", "about", "above", "after", "again", "all", "also", "am", "as",
        "because", "before", "between", "both", "each", "few", "he", "her",
        "here", "him", "his", "how", "i", "into", "its", "me", "more", "most",
        "my", "new", "now", "only", "other", "our", "out", "over", "own",
        "same", "she", "some", "such", "their", "them", "there", "these",
        "they", "through", "up", "we", "what", "when", "where", "which",
        "while", "who", "whom", "why", "you", "your",
    }

    words = text.lower().split()
    word_freq: dict[str, int] = {}

    for word in words:
        clean = "".join(c for c in word if c.isalnum())
        if clean and len(clean) > 3 and clean not in stop_words:
            word_freq[clean] = word_freq.get(clean, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    return [{"keyword": w, "score": f} for w, f in sorted_words[:top_n]]


def compute_text_stats(text: str) -> dict:
    """Compute word count, character count, sentence count, and reading time."""
    words = text.split()
    sentences = [s for s in text.split(".") if s.strip()]
    return {
        "word_count": len(words),
        "char_count": len(text),
        "sentence_count": len(sentences),
        "reading_time_minutes": max(1, round(len(words) / 200)),
    }
