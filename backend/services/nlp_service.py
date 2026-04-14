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
from deep_translator import GoogleTranslator
import urllib.parse

from database import SessionLocal
from models import CaseDocument
from services.vector_service import vector_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# BART Pipeline (lazy-loaded singleton)
# ──────────────────────────────────────────────────────────────

_bart_pipeline = None
_bart_load_attempted = False


def _get_bart_pipeline():
    """Load the BART summarization model and tokenizer once, on first call."""
    global _bart_pipeline, _bart_load_attempted

    if _bart_load_attempted:
        return _bart_pipeline

    _bart_load_attempted = True
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline as hf_pipeline
        logger.info("Loading facebook/bart-large-cnn components (first request may take a minute)...")
        
        # Load model and tokenizer directly to avoid 'Unknown task' registry errors
        model_name = "facebook/bart-large-cnn"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        
        _bart_pipeline = hf_pipeline(
            "summarization",
            model=model,
            tokenizer=tokenizer,
            device=-1,  # CPU
        )
        logger.info("BART model loaded successfully via manual component loading.")
    except Exception as exc:
        logger.warning("Could not load BART model components — falling back to extractive: %s", exc)
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
# Legal citation patterns
# ──────────────────────────────────────────────────────────────

CITATION_PATTERNS = {
    # US Supreme Court and Federal Reporter
    "us_supreme_court": r'\b\d+\s*U\.?S\.?\s*\d+\b',
    "federal_reporter": r'\b\d+\s+F\.?\d*d\.?\s*\d+\b',
    "federal_supplement": r'\b\d+\s+F\.?\s*Supp\.?\s*\d+\b',

    # US Code (statutes)
    "us_code": r'\b\d+\s*U\.?S\.?C\.?\s*§?\s*\d+[a-zA-Z0-9\-]*\b',

    # Indian Legal Citations
    "indian_sc": r'\b(?:AIR|S\.?C\.?C\.?|SCR)\s*\d{4}\s*(?:SC|SCC|SCR)?\s*\d+\b',
    "indian_case_year": r'\b\[\s*\d{4}\s*\]\s*\d+\s*[A-Z]+\.?\s*\d+\b',
    "indian_statute": r'\b(?:The\s+)?[A-Z][a-zA-Z\s]+(?:Act|Code|Rules|Regulations)\b(?:\s*,?\s*\d{4})?',

    # Case citations (Party v. Party)
    "case_citation": r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+v\.?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b',

    # Common law reports
    "law_report": r'\b\d+\s+[A-Z]{2,}\s+\d+\b',

    # Section references
    "section_ref": r'\b(?:section|sec\.?|§)\s*\d+[a-zA-Z0-9\-]*(?:\s*\(\d+\))?\b',
}


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def translate_to_english(text: str) -> str:
    """
    Translates input text to English, splitting into chunks if necessary to bypass API limits.
    """
    if not text or len(text.strip()) == 0:
        return text

    try:
        translator = GoogleTranslator(source='auto', target='en')
        if len(text) > 4000:
            chunks = _split_into_chunks(text, 4000)
            translated_chunks = [translator.translate(chunk) for chunk in chunks]
            return " ".join(translated_chunks)
        else:
            return translator.translate(text)
    except Exception as e:
        logger.error(f"Input translation to English failed: {e}")
        return text

def summarize_text(text: str, length: str = "medium", language: str = "en") -> dict:
    """
    Summarize *text* using BART (abstractive) with an automatic fallback
    to extractive summarization if the model is unavailable.
    """
    if length not in BART_LENGTHS:
        length = "medium"

    # Ensure input text is translated to English for processing
    english_text = translate_to_english(text)

    # RAG: Check for similar past cases
    context_prefix = ""
    similar_cases = vector_service.find_similar(english_text, top_k=1, threshold=0.75)
    
    if similar_cases:
        case_id = similar_cases[0][0]
        db = SessionLocal()
        try:
            past_case = db.query(CaseDocument).filter(CaseDocument.id == case_id).first()
            if past_case and past_case.summary_text:
                context_prefix = f"[Reference style from similar case: {past_case.summary_text}]\n\n"
                logger.info(f"RAG Context added from past case ID {case_id}")
        except Exception as e:
            logger.error(f"Error fetching past case for RAG: {e}")
        finally:
            db.close()

    pipe = _get_bart_pipeline()

    if pipe is not None:
        result = _bart_summarize(pipe, english_text, length, context_prefix=context_prefix)
    else:
        result = _extractive_summarize(english_text, length)

    # Multi-language translation
    if language and language != "en":
        try:
            translator = GoogleTranslator(source='auto', target=language)
            # Split summary into chunks if it is too long (deep_translator has 5000 limit)
            summary_text = result["summary"]
            if len(summary_text) > 4000:
                chunks = _split_into_chunks(summary_text, 4000)
                translated_chunks = [translator.translate(chunk) for chunk in chunks]
                result["summary"] = " ".join(translated_chunks)
            else:
                result["summary"] = translator.translate(summary_text)
            result["language"] = language
        except Exception as e:
            logger.error(f"Translation failed: {e}")

    return result


# ──────────────────────────────────────────────────────────────
# BART abstractive summarization
# ──────────────────────────────────────────────────────────────

def _bart_summarize(pipe, text: str, length: str, context_prefix: str = "") -> dict:
    """Run BART abstractive summarization, chunking if needed."""
    max_len, min_len = BART_LENGTHS[length]

    chunks = _split_into_chunks(text, BART_CHUNK_CHARS)
    logger.info("Summarising %d chunk(s) with BART [%s]", len(chunks), length)

    partial_summaries = []
    for i, chunk in enumerate(chunks):
        # We only prepend the RAG context to the first chunk
        chunk_with_context = (context_prefix + chunk) if i == 0 else chunk
        
        # Ensure min_len doesn't exceed the chunk word count
        chunk_words = len(chunk.split())
        effective_min = min(min_len, max(10, chunk_words // 3))
        effective_max = min(max_len, max(20, chunk_words))

        if effective_min >= effective_max:
            effective_min = max(10, effective_max - 10)

        try:
            out = pipe(
                chunk_with_context,
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
    
    # Ensure input text is translated to English for SpaCy NER processing
    english_text = translate_to_english(text)

    if nlp is not None:
        return _extract_keywords_ner(nlp, english_text, top_n)

    # Fallback: pure frequency (adds "FREQUENCY" type for consistency)
    freq_keywords = _extract_keywords_frequency(english_text, top_n)
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


# ──────────────────────────────────────────────────────────────
# Citation extraction
# ──────────────────────────────────────────────────────────────

def extract_citations(text: str) -> list[dict]:
    """
    Extract legal citations from text using regex patterns.

    Returns a list of dicts:
        {"citation": str, "type": str, "position": [start, end]}
    """
    citations = []
    seen = set()  # Track unique citations

    for cite_type, pattern in CITATION_PATTERNS.items():
        try:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                citation_text = match.group().strip()
                # Skip if already seen (case-insensitive)
                if citation_text.lower() in seen:
                    continue
                seen.add(citation_text.lower())

                # Generate Search Link
                encoded_cite = urllib.parse.quote(citation_text)
                if cite_type == "us_code":
                    link_url = f"https://law.justia.com/search?query={encoded_cite}"
                elif cite_type in ("case_citation", "law_report"):
                    link_url = f"https://scholar.google.com/scholar?hl=en&q={encoded_cite}"
                else:
                    # Default / Indian databases
                    link_url = f"https://indiankanoon.org/search/?formInput={encoded_cite}"

                citations.append({
                    "citation": citation_text,
                    "type": cite_type.replace("_", " ").title(),
                    "position": [match.start(), match.end()],
                    "link": link_url
                })
        except re.error:
            logger.warning(f"Invalid regex pattern for {cite_type}")
            continue

    # Sort by position
    citations.sort(key=lambda x: x["position"][0])

    return citations

def _extract_entities_by_type(text: str) -> dict:
    """
    Extract ALL named entities from text grouped by type.
    Runs NER on both raw text AND English translation to catch everything.
    Returns dict like: {"PERSON": {"john doe": "John Doe"}, "DATE": {"2024": "2024"}, ...}
    Keys are lowercased for comparison, values are original display text.
    """
    nlp = _get_spacy_nlp()
    if nlp is None:
        return {}

    max_chars = 100_000

    # Run NER on raw text first (catches original names/institutes)
    raw_text = text[:max_chars] if len(text) > max_chars else text
    entities: dict[str, dict[str, str]] = {}  # {TYPE: {lowercase: display_text}}

    try:
        doc_raw = nlp(raw_text)
        for ent in doc_raw.ents:
            clean = " ".join(ent.text.split()).strip()
            if len(clean) < 2:
                continue
            bucket = entities.setdefault(ent.label_, {})
            bucket[clean.lower()] = clean  # lowercase key, original display
    except Exception:
        pass

    # Also run on English translation to catch anything missed
    try:
        english_text = translate_to_english(text)
        eng_text = english_text[:max_chars] if len(english_text) > max_chars else english_text
        doc_eng = nlp(eng_text)
        for ent in doc_eng.ents:
            clean = " ".join(ent.text.split()).strip()
            if len(clean) < 2:
                continue
            bucket = entities.setdefault(ent.label_, {})
            key = clean.lower()
            if key not in bucket:
                bucket[key] = clean
    except Exception:
        pass

    return entities


# User-friendly labels for SpaCy entity types
_ENTITY_LABELS = {
    "PERSON": "Persons / Names",
    "ORG": "Organizations / Institutes",
    "GPE": "Jurisdictions / Locations",
    "LOC": "Locations",
    "DATE": "Dates",
    "LAW": "Laws / Statutes",
    "EVENT": "Events",
    "NORP": "Groups / Nationalities",
    "MONEY": "Monetary Values",
    "FAC": "Facilities / Institutes",
    "CARDINAL": "Numbers",
    "ORDINAL": "Ordinal Numbers",
    "QUANTITY": "Quantities",
    "PRODUCT": "Products",
    "WORK_OF_ART": "Works / Titles",
    "LANGUAGE": "Languages",
    "TIME": "Times",
    "PERCENT": "Percentages",
}


import re

def _ultra_normalize(text: str) -> str:
    """Normalize text by removing all special chars, extra whitespace, and lowercasing."""
    # Replace all non-alphanumeric with space
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    # Collapse multiple spaces
    return " ".join(text.lower().split()).strip()

def _find_shared_blocks(text1: str, text2: str) -> list[str]:
    """
    Find shared sentences using a fuzzy token-overlap approach.
    Handles differences in punctuation, dashes, and whitespace across PDF versions.
    """
    try:
        nlp = _get_spacy_nlp()
        if not nlp:
            return []

        # Process reasonable text chunks for NLP
        doc1 = nlp(text1[:60000]) if len(text1) > 60000 else nlp(text1)
        doc2 = nlp(text2[:60000]) if len(text2) > 60000 else nlp(text2)

        # Helper to get sequence of content-rich tokens
        def get_content_tokens(sent_text):
            # We don't use full spacy objects here to keep it fast
            words = _ultra_normalize(sent_text).split()
            # Return words that aren't trivial (too short or just generic joining words)
            # We filter out very short words, but keep those that might be part of an acronym
            return [w for w in words if len(w) > 1]

        # Break into sentences
        sents1 = [s.text for s in doc1.sents if len(s.text.strip()) > 10]
        sents2 = [s.text for s in doc2.sents if len(s.text.strip()) > 10]

        # ADDITION: Add raw lines as "pseudo-sentences" to catch headers that SpaCy might merge
        lines1 = [line.strip() for line in text1[:10000].split('\n') if len(line.strip()) > 15]
        lines2 = [line.strip() for line in text2[:10000].split('\n') if len(line.strip()) > 15]
        
        all_s1 = sents1 + lines1
        all_s2 = sents2 + lines2

        shared = []
        
        # Pre-calculate content sets for doc2 to avoid redundant work
        sent2_data = []
        for s2 in all_s2:
            tokens = set(get_content_tokens(s2))
            if len(tokens) >= 3: # Lower threshold for headers
                sent2_data.append({"text": s2, "tokens": tokens})

        for s1 in all_s1:
            tokens1 = set(get_content_tokens(s1))
            if len(tokens1) < 3:
                continue

            best_match = None
            max_sim = 0.0

            for s2_item in sent2_data:
                tokens2 = s2_item["tokens"]
                
                # Jaccard Similarity: Intersection / Union
                intersection = tokens1.intersection(tokens2)
                if not intersection:
                    continue
                
                union = tokens1.union(tokens2)
                sim = len(intersection) / len(union)

                if sim > max_sim:
                    max_sim = sim
                    best_match = s2_item["text"]
                
                # Early exit if we have a very strong match
                if sim >= 0.95:
                    break
            
            # If similarity threshold met (70% for broader matching), count as shared
            if max_sim >= 0.70:
                cleaned_match = " ".join(best_match.split()).strip()
                if cleaned_match not in shared:
                    shared.append(cleaned_match)
        
        return shared
    except Exception as e:
        logger.error(f"Error in fuzzy shared block detection: {str(e)}")
        return []


def compare_documents(text1: str, text2: str, language: str = "en") -> dict:
    """
    Compare two documents by extracting structured entities, 
    shared content blocks, and topical similarities.
    """
    try:
        # Step 1: Summarize both documents
        sum1 = summarize_text(text1, length="medium")["summary"]
        sum2 = summarize_text(text2, length="medium")["summary"]

        # Step 2: Extract entities grouped by type from both docs
        ents1 = _extract_entities_by_type(text1)
        ents2 = _extract_entities_by_type(text2)

        # Step 3: Find identical blocks (the institutional names/Degree requirements)
        shared_blocks = _find_shared_blocks(text1, text2)

        # Step 4: Compute similarities and differences per entity type
        # (case-insensitive comparison using lowercase keys)
        all_types = set(list(ents1.keys()) + list(ents2.keys()))

        similarities = []
        differences = []

        for etype in sorted(all_types):
            label = _ENTITY_LABELS.get(etype, etype)
            dict1 = ents1.get(etype, {})  # {lowercase: display}
            dict2 = ents2.get(etype, {})

            keys1 = set(dict1.keys())
            keys2 = set(dict2.keys())

            shared_keys = keys1 & keys2
            only1_keys = keys1 - keys2
            only2_keys = keys2 - keys1

            if shared_keys:
                similarities.append({
                    "category": label,
                    "items": sorted([dict1[k] for k in shared_keys])
                })

            if only1_keys or only2_keys:
                differences.append({
                    "category": label,
                    "only_in_doc1": sorted([dict1[k] for k in only1_keys]),
                    "only_in_doc2": sorted([dict2[k] for k in only2_keys])
                })

        # Step 4: Also extract shared topic keywords (frequency-based)
        k1 = extract_keywords(text1, top_n=20)
        k2 = extract_keywords(text2, top_n=20)
        topic_set1 = {k["keyword"].lower() for k in k1}
        topic_set2 = {k["keyword"].lower() for k in k2}
        shared_topics = sorted(topic_set1 & topic_set2)
        unique_topics_1 = sorted(topic_set1 - topic_set2)
        unique_topics_2 = sorted(topic_set2 - topic_set1)

        # Step 5: Build comparison summary
        comparison_summary = (
            f"Document 1 Summary:\n{sum1}\n\n"
            f"Document 2 Summary:\n{sum2}"
        )

        # Step 6: Translate if needed
        if language != "en":
            try:
                translator = GoogleTranslator(source='en', target=language)
                if len(comparison_summary) > 4000:
                    chunks = _split_into_chunks(comparison_summary, 4000)
                    translated_chunks = [translator.translate(chunk) for chunk in chunks]
                    comparison_summary = " ".join(translated_chunks)
                else:
                    comparison_summary = translator.translate(comparison_summary)
            except Exception as e:
                logger.error(f"Outbound comparison translation failed: {str(e)}")

        return {
            "document_1_summary": sum1,
            "document_2_summary": sum2,
            "comparison_summary": comparison_summary,
            "similarities": similarities,
            "differences": differences,
            "shared_topics": shared_topics,
            "shared_blocks": shared_blocks,
            "unique_topics_doc1": unique_topics_1,
            "unique_topics_doc2": unique_topics_2,
            "shared_entities": shared_topics  # backward compat
        }
    except Exception as e:
        logger.error(f"Comparison pipeline error: {str(e)}")
        raise e
