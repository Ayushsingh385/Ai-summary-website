"""
NLP Service — Summarization, keyword extraction, and text analysis.
Uses a statistical Extractive Summarization algorithm to ensure compatibility
across all Python versions without needing heavy compiled dependencies.
"""

import re
import math
import logging

logger = logging.getLogger(__name__)

# Summary length presets: target sentence count roughly
SUMMARY_LENGTHS = {
    "short":  3,    # ~50-80 words
    "medium": 7,    # ~100-150 words
    "long":   15,   # ~200-300 words
}


def _get_sentences(text: str) -> list[str]:
    """Split text into sentences using simple regex."""
    text = re.sub(r'\s+', ' ', text)
    # Match sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def summarize_text(text: str, length: str = "medium") -> dict:
    """
    Generate an extractive summary of the provided text by scoring sentences.
    """
    if length not in SUMMARY_LENGTHS:
        length = "medium"

    target_sentences = SUMMARY_LENGTHS[length]
    sentences = _get_sentences(text)
    
    if len(sentences) <= target_sentences:
        # Text is already shorter than target summary
        combined_summary = " ".join(sentences)
    else:
        # 1. Calculate word frequencies (ignoring common stop words)
        words = _extract_keywords_frequency(text, top_n=100)
        word_scores = {w['keyword']: w['score'] for w in words}

        # 2. Score sentences based on word frequencies
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = 0
            s_words = [re.sub(r'\W+', '', w.lower()) for w in sentence.split()]
            for word in s_words:
                if word in word_scores:
                    score += word_scores[word]
            
            # Normalize by length to not overly favor long sentences
            # but also give a slight boost to early sentences (often topic sentences)
            position_boost = 1.0 if i > 3 else 1.5
            normalized_score = (score / (len(s_words) + 1)) * position_boost
            sentence_scores.append((normalized_score, i, sentence))

        # 3. Sort by score descending, pick top N
        sentence_scores.sort(key=lambda x: x[0], reverse=True)
        top_sentences = sentence_scores[:target_sentences]

        # 4. Sort back to original document order
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
    }


def extract_keywords(text: str, top_n: int = 15) -> list[dict]:
    """
    Extract keywords using frequency-based approach.
    """
    return _extract_keywords_frequency(text, top_n)


def _extract_keywords_frequency(text: str, top_n: int = 15) -> list[dict]:
    """Fallback keyword extraction using word frequency analysis."""
    # Common English stop words
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
    word_freq = {}

    for word in words:
        # Clean punctuation
        clean = "".join(c for c in word if c.isalnum())
        if clean and len(clean) > 3 and clean not in stop_words:
            word_freq[clean] = word_freq.get(clean, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    return [
        {"keyword": w, "score": f}
        for w, f in sorted_words[:top_n]
    ]


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
