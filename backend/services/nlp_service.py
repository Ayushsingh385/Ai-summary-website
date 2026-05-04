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
import torch
from transformers import pipeline as hf_pipeline

from database import SessionLocal
from models import CaseDocument
from services.vector_service import vector_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Regex Fragments (to avoid over-eager IDE "path" detection in strings)
# ──────────────────────────────────────────────────────────────
_D = r'[0-9]'
_D_1_2 = _D + r'{1,2}'
_D_4 = _D + r'{4}'
_D_PLUS = _D + r'+'
_W = r'[a-zA-Z0-9]'
_S = r'\s'
_SP = r'\s+'


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
            device=0 if torch.cuda.is_available() else -1,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        logger.info(f"BART model loaded successfully on {'GPU (FP16)' if torch.cuda.is_available() else 'CPU'}.")
    except Exception as exc:
        logger.warning("Could not load BART pipeline — attempting direct model use: %s", exc)
        try:
            # Fallback for when 'summarization' task is not in registry
            # We already have model and tokenizer from above in the local scope? 
            # Wait, I need to make sure they are available here.
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            model_name = "facebook/bart-large-cnn"
            m_tokenizer = AutoTokenizer.from_pretrained(model_name)
            m_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            class SimpleBART:
                def __init__(self, model, tokenizer):
                    self.model = model
                    self.tokenizer = tokenizer
                def __call__(self, text, **kwargs):
                    # Basic implementation of summarization generation
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(device)
                    self.model.to(device)
                    summary_ids = self.model.generate(
                        inputs["input_ids"],
                        max_length=kwargs.get("max_length", 142),
                        min_length=kwargs.get("min_length", 30),
                        do_sample=kwargs.get("do_sample", False),
                        early_stopping=True,
                        num_beams=2
                    )
                    return [{"summary_text": self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)}]
            
            _bart_pipeline = SimpleBART(m_model, m_tokenizer)
            logger.info("BART model loaded successfully via direct wrapper.")
        except Exception as fallback_exc:
            logger.error("Total BART failure: %s", fallback_exc)
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

# BART length params (max_length, min_length)
BART_LENGTHS = {
    "short":  (100, 50),
    "medium": (190, 150),
    "long":   (300, 250),
}

# Extractive fallback: target sentence count
EXTRACTIVE_LENGTHS = {
    "short":  5,
    "medium": 10,
    "long":   16,
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
    "us_supreme_court": r'\b' + _D_PLUS + r'\s*U\.?S\.?\s*' + _D_PLUS + r'\b',
    "federal_reporter": r'\b' + _D_PLUS + r'\s+F\.?' + _D + r'*d\.?\s*' + _D_PLUS + r'\b',
    "federal_supplement": r'\b' + _D_PLUS + r'\s+F\.?\s*Supp\.?\s*' + _D_PLUS + r'\b',

    # US Code (statutes)
    "us_code": r'\b' + _D_PLUS + r'\s*U\.?S\.?C\.?\s*§?\s*' + _D_PLUS + _W + r'*\b',

    # Indian Legal Citations
    "indian_sc": r'\b(?:AIR|S\.?C\.?C\.?|SCR)\s*' + _D_4 + r'\s*(?:SC|SCC|SCR)?\s*' + _D_PLUS + r'\b',
    "indian_case_year": r'\b\[\s*' + _D_4 + r'\s*\]\s*' + _D_PLUS + r'\s*[A-Z]+\.?\s*' + _D_PLUS + r'\b',
    "indian_statute": r'\b(?:The\s+)?[A-Z][a-zA-Z\s]+(?:Act|Code|Rules|Regulations)\b(?:\s*,?\s*' + _D_4 + r')?',

    # Case citations (Party v. Party)
    "case_citation": r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+v\.?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b',

    # Common law reports
    "law_report": r'\b' + _D_PLUS + r'\s+[A-Z]{2,}\s+' + _D_PLUS + r'\b',

    # Section references
    "section_ref": r'\b(?:section|sec\.?|§)\s*' + _D_PLUS + _W + r'*(?:\s*\(' + _D_PLUS + r'\))?\b',
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

    # 1. Attempt Advanced Summarization via configured LLM providers
    from services.llm_service import get_llm_response
    
    system_prompt = (
        "You are an expert administrative assistant for Zilla Parishad. "
        "Your task is to summarize official documents, letters, or case files concisely. "
        "Maintain a professional tone and ensure all key entities (names, dates, amounts) are preserved. "
        "Write in proper grammatical sentences and ensure the summary has a clear beginning, middle, and end."
    )
    # Calculate dynamic word target — higher ratios for short docs, tighter for long
    original_word_count = len(english_text.split())
    if original_word_count < 1500:
        llm_percentages = {"short": 0.12, "medium": 0.20, "long": 0.30}
        llm_minimums = {"short": 50, "medium": 100, "long": 150}
    else:
        llm_percentages = {"short": 0.05, "medium": 0.10, "long": 0.15}
        llm_minimums = {"short": 50, "medium": 100, "long": 150}
    target_words = max(llm_minimums.get(length, 100), int(original_word_count * llm_percentages.get(length, 0.10)))
    
    user_msg = f"Summarize the following document in approximately {target_words} words:\n\n{english_text}"
    
    try:
        logger.info("Attempting abstractive summarization via LLM providers...")
        llm_out = get_llm_response(user_message=user_msg, system_prompt=system_prompt)
        summary_text = llm_out.get("response", "")
        provider = llm_out.get("provider", "unknown")
        
        # Check if it hit the offline fallback text
        if provider != "offline" and summary_text and len(summary_text.strip()) > 50:
            logger.info(f"LLM Summarization successful via {provider}!")
            result = {
                "summary": summary_text.strip(),
                "method": f"{provider}-abstractive",
                "original_word_count": len(english_text.split()),
                "summary_word_count": len(summary_text.split())
            }
        else:
            raise Exception("LLM provider returned offline fallback or empty response.")
    except Exception as e:
        logger.warning(f"LLM providers failed ({e}), falling back to local processing.")
        
        # 2. Local BART Fallback — ONLY for short documents (<1500 words)
        #    BART can only handle ~1024 tokens. For longer docs, its pre-condensation
        #    step destroys too much content, producing tiny, incoherent summaries.
        word_count = len(english_text.split())
        pipe = _get_bart_pipeline()
        if pipe is not None and word_count < 1500:
            logger.info("Using local BART abstractive summarization for short document...")
            result = _bart_summarize(pipe, english_text, length, context_prefix)
        else:
            # 3. Structured Extractive Summarization for long documents
            if word_count >= 1500:
                logger.info(f"Document is {word_count} words — too long for BART. Using structured extractive summarization...")
            else:
                logger.warning("BART unavailable, using structured extractive summarization...")
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
    """Run BART abstractive summarization with a fast two-stage approach.
    
    Stage 1: If text is too long, use instant extractive summarization to condense it.
    Stage 2: Run BART only ONCE on the condensed text (instead of 10+ times on chunks).
    This is ~10x faster than the old chunk-by-chunk approach.
    """
    max_len, min_len = BART_LENGTHS[length]

    # Stage 1: Pre-condense long text using extractive summarization (instant, <0.1s)
    text_chars = len(text)
    if text_chars > BART_CHUNK_CHARS:
        logger.info("Fast mode: Pre-condensing %d chars with extractive pass first...", text_chars)
        # Extract the most important sentences to fit within BART's input window
        sentences = _get_sentences(text)
        
        if len(sentences) > 5:
            # Score sentences by keyword frequency
            words = _extract_keywords_frequency(text, top_n=100)
            word_scores = {w["keyword"]: w["score"] for w in words}
            
            sentence_scores = []
            for i, sentence in enumerate(sentences):
                score = 0
                s_words = [re.sub(r"\W+", "", w.lower()) for w in sentence.split()]
                for word in s_words:
                    if word in word_scores:
                        score += word_scores[word]
                position_boost = 1.5 if i < 3 else (1.2 if i >= len(sentences) - 2 else 1.0)
                normalized_score = (score / (len(s_words) + 1)) * position_boost
                sentence_scores.append((normalized_score, i, sentence))
            
            sentence_scores.sort(key=lambda x: x[0], reverse=True)
            
            # Keep enough top sentences to fill one BART chunk
            kept = []
            total_chars = 0
            for score, idx, sent in sentence_scores:
                if total_chars + len(sent) > BART_CHUNK_CHARS:
                    break
                kept.append((idx, sent))
                total_chars += len(sent)
            
            # Restore original order
            kept.sort(key=lambda x: x[0])
            text = " ".join([s for _, s in kept])
            logger.info("Condensed to %d chars for single BART pass.", len(text))

    # Stage 2: Single BART call on the (possibly condensed) text
    chunk_with_context = context_prefix + text if context_prefix else text
    
    chunk_words = len(text.split())
    effective_min = min(min_len, max(10, chunk_words // 3))
    effective_max = min(max_len, max(20, chunk_words))
    if effective_min >= effective_max:
        effective_min = max(10, effective_max - 10)

    logger.info("Running single BART pass [%s] (min=%d, max=%d)...", length, effective_min, effective_max)
    
    try:
        out = pipe(
            chunk_with_context,
            max_length=effective_max,
            min_length=effective_min,
            do_sample=False,
            truncation=True,
            num_beams=2,
        )
        combined_summary = out[0]["summary_text"]
    except Exception as exc:
        logger.warning("BART failed, using extractive fallback: %s", exc)
        return _extractive_summarize(text, length)

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
    Generate a flowing extractive summary by scoring sentences on word frequency
    and position, then selecting the most important sentences up to a word budget.
    Summary length is proportional to the original document size:
      - short:  15% of original word count
      - medium: 25% of original word count
      - long:   40% of original word count
    
    Sentences are drawn from the opening, body, and closing of the document
    to ensure coverage, then merged into a single flowing paragraph in their
    original order.
    """
    # Dynamic word target based on document size
    original_word_count = len(text.split())
    if original_word_count < 1500:
        LENGTH_PERCENTAGES = {"short": 0.12, "medium": 0.20, "long": 0.30}
        LENGTH_MINIMUMS = {"short": 50, "medium": 100, "long": 150}
    else:
        LENGTH_PERCENTAGES = {"short": 0.05, "medium": 0.10, "long": 0.15}
        LENGTH_MINIMUMS = {"short": 50, "medium": 100, "long": 150}
    percentage = LENGTH_PERCENTAGES.get(length, 0.10)
    minimum = LENGTH_MINIMUMS.get(length, 100)
    target_words = max(minimum, int(original_word_count * percentage))

    logger.info(
        "Extractive summary: %d original words × %d%% = target ~%d words",
        original_word_count, int(percentage * 100), target_words
    )

    sentences = _get_sentences(text)

    # Deduplicate sentences BEFORE scoring — no repeated lines ever
    seen_normalized = set()
    unique_sentences = []
    for sent in sentences:
        # Normalize: lowercase, strip extra whitespace/punctuation for comparison
        norm = re.sub(r'\s+', ' ', sent.strip().lower())
        norm = re.sub(r'[^\w\s]', '', norm)
        if norm and norm not in seen_normalized:
            seen_normalized.add(norm)
            unique_sentences.append(sent)
    sentences = unique_sentences

    # If the document is already short enough, return it as-is
    if original_word_count <= target_words:
        combined_summary = " ".join(sentences)
    else:
        # Score sentences by keyword relevance + position
        words = _extract_keywords_frequency(text, top_n=100)
        word_scores = {w["keyword"]: w["score"] for w in words}

        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = 0
            s_words = [re.sub(r"\W+", "", w.lower()) for w in sentence.split()]
            for word in s_words:
                if word in word_scores:
                    score += word_scores[word]

            # Position-based boosting for document structure
            total_sents = len(sentences)
            if i < 5:
                # Opening sentences — usually contain the subject/topic
                position_boost = 1.8
            elif i >= total_sents - 3:
                # Closing sentences — usually contain conclusions/orders
                position_boost = 1.5
            elif i < total_sents * 0.15:
                # Early section — background/context
                position_boost = 1.3
            elif i >= total_sents * 0.85:
                # Late section — decisions/outcomes
                position_boost = 1.3
            else:
                position_boost = 1.0

            normalized_score = (score / (len(s_words) + 1)) * position_boost
            sentence_scores.append((normalized_score, i, sentence))

        # Sort by score (best first)
        sentence_scores.sort(key=lambda x: x[0], reverse=True)

        # Allocate word budget across 3 sections
        overview_budget = int(target_words * 0.20)   # 20% for opening
        body_budget = int(target_words * 0.60)        # 60% for key details
        conclusion_budget = int(target_words * 0.20)  # 20% for closing

        total_sents = len(sentences)
        opening_range = set(range(0, min(int(total_sents * 0.15), total_sents)))
        closing_range = set(range(max(int(total_sents * 0.85), 0), total_sents))
        body_range = set(range(total_sents)) - opening_range - closing_range

        def pick_sentences(scored_sents, allowed_indices, budget):
            picked = []
            current_words = 0
            for score, idx, sent in scored_sents:
                if idx not in allowed_indices:
                    continue
                sent_words = len(sent.split())
                if current_words + sent_words > budget and picked:
                    break
                picked.append((idx, sent))
                current_words += sent_words
            return picked

        overview_sents = pick_sentences(sentence_scores, opening_range, overview_budget)
        body_sents = pick_sentences(sentence_scores, body_range, body_budget)
        conclusion_sents = pick_sentences(sentence_scores, closing_range, conclusion_budget)

        # Restore original document order within each section
        overview_sents.sort(key=lambda x: x[0])
        body_sents.sort(key=lambda x: x[0])
        conclusion_sents.sort(key=lambda x: x[0])

        # Merge all selected sentences into one flowing summary
        all_selected = overview_sents + body_sents + conclusion_sents
        # Restore original document order across all sections
        all_selected.sort(key=lambda x: x[0])
        combined_summary = " ".join([s for _, s in all_selected])

        # If somehow sections are empty, fall back to flat selection
        if not combined_summary.strip():
            selected = []
            current_words = 0
            for score, idx, sent in sentence_scores:
                sent_words = len(sent.split())
                if current_words + sent_words > target_words and selected:
                    break
                selected.append((idx, sent))
                current_words += sent_words
            selected.sort(key=lambda x: x[0])
            combined_summary = " ".join([s for _, s in selected])

    summary_word_count = len(combined_summary.split())
    compression = round(
        (1 - summary_word_count / max(original_word_count, 1)) * 100, 1
    )

    return {
        "summary": combined_summary,
        "summary_word_count": summary_word_count,
        "original_word_count": original_word_count,
        "compression_ratio": compression,
        "target_word_count": target_words,
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
# Case Type Classification
# ──────────────────────────────────────────────────────────────

CASE_TYPE_KEYWORDS = {
    "Criminal": [
        "criminal", "murder", "theft", "assault", "jail", "prison", "fIR", "police",
        "arrest", "bail", " ipc ", "indian penal code", "homicide", "robbery",
        "dacoity", "kidnapping", "rape", "fraud", "forgery", "cheating",
        "weapon", "accused", "convict", "sentenced", "prosecution", "offense",
        "offence", "investigation", "charge sheet", "cognizable", "cognizance"
    ],
    "Civil": [
        "civil", "property", "tenant", "landlord", "dispute", "eviction", "injunction",
        "specific performance", "contract", "breach", "damages", "tort", "negligence",
        "consumer", "compensation", "suit", "plaint", "defendant", "plaintiff",
        "decree", "execution", "attachment", "sale deed", "title", "possession"
    ],
    "Family": [
        "divorce", "maintenance", "custody", "marriage", "family", "alimony",
        "child support", "guardian", "matrimony", "dowry", "domestic violence",
        "separation", "annulment", "hindu marriage act", "muslim personal law",
        "adoption", "legitimacy", "conjugal rights"
    ],
    "Corporate": [
        "company", "corporate", "shareholder", "business", "director", "board",
        "companies act", "LLP", "partnership", "merger", "acquisition",
        "insolvency", "bankruptcy", "liquidation", "creditor", "debtor",
        "security", "equity", "dividend", "stocks", "nclt", "roc"
    ],
    "Constitutional": [
        "fundamental rights", "constitution", "writ petition", "article 14",
        "article 21", "article 19", "supreme court", "high court", "judicial review",
        "public interest litigation", "pil", "constitutional", "amendment",
        "federal", "state", "centre", "legislature", "parliament"
    ],
    "Tax": [
        "income tax", "gst", "tax", "excise", "customs", "vat", "assessment",
        "itr", "deduction", "exemption", "refund", "penalty", "scrutiny",
        "cbd", "taxable", "assessment year", "previous year", "tcs", "tds"
    ],
    "Labor & Employment": [
        "labor", "labour", "employment", "workman", "industrial dispute",
        "trade union", "strike", "lockout", "wages", "gratuity", "provident fund",
        "epf", "esic", "termination", "retrenchment", "settlement", "conciliation"
    ],
    "Land & Revenue": [
        "land acquisition", "revenue", "land records", "mutation", "patta",
        "tenancy", "agricultural", "ceiling", "consolidation", "survey",
        "settlement", "khasra", "khatauni", "jamabandi", "land reform"
    ],
    "Intellectual Property": [
        "patent", "trademark", "copyright", "intellectual property", "ipr",
        "infringement", "license", "royalty", "trade secret", "geographical indication",
        "design", "brand", "logo", "creative work", "piracy"
    ],
    "Environmental": [
        "environment", "pollution", "forest", "wildlife", "eco", "green tribunal",
        "ngt", "environmental clearance", "hazardous", "waste", "air quality",
        "water pollution", "biodiversity", "conservation", "sustainable"
    ]
}


def classify_case_type(text: str) -> dict:
    """
    Classify the legal case type based on text content.

    Returns a dict with:
        - primary_type: The most likely case category
        - confidence: Confidence score (0-100)
        - all_scores: Breakdown of scores for all categories
        - matched_keywords: Keywords that triggered the classification
    """
    if not text or len(text.strip()) < 20:
        return {
            "primary_type": "Unknown",
            "confidence": 0,
            "all_scores": {},
            "matched_keywords": []
        }

    text_lower = text.lower()

    # Score each category
    scores = {}
    matched = {}

    for case_type, keywords in CASE_TYPE_KEYWORDS.items():
        score = 0
        matched_kw = []

        for kw in keywords:
            if kw.lower() in text_lower:
                # Weight by keyword specificity (longer = more specific)
                weight = len(kw.split()) if len(kw.split()) > 1 else 1
                score += weight
                matched_kw.append(kw.strip())

        scores[case_type] = score
        matched[case_type] = matched_kw

    # Get total score for confidence calculation
    total_score = sum(scores.values()) or 1

    # Find primary type
    if all(s == 0 for s in scores.values()):
        return {
            "primary_type": "Misc/Other",
            "confidence": 0,
            "all_scores": {},
            "matched_keywords": []
        }

    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_type, primary_score = sorted_types[0]

    # Calculate confidence based on score distribution
    confidence = round((primary_score / total_score) * 100, 1)

    # Normalize scores to percentages
    all_scores = {k: round((v / total_score) * 100, 1) if total_score > 0 else 0
                  for k, v in scores.items() if v > 0}

    return {
        "primary_type": primary_type,
        "confidence": min(confidence, 100),
        "all_scores": dict(sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:5]),
        "matched_keywords": matched[primary_type][:10]  # Top 10 matched keywords
    }


# ──────────────────────────────────────────────────────────────
# Legal Document Analysis Features
# ──────────────────────────────────────────────────────────────

def extract_legal_issues(text: str) -> list[dict]:
    """
    Extract key legal issues/questions from a legal document.
    Looks for patterns like "Issue:", "Question:", "Whether", etc.
    """
    if not text or len(text.strip()) < 100:
        return []

    issues = []
    text_lower = text.lower()

    # Pattern 1: Explicit issue markers
    issue_patterns = [
        r'issue[s]?\s*(?:' + _D_PLUS + r'\.|\:|\-)\s*([^\n]+)',
        r'question[s]?\s*(?:' + _D_PLUS + r'\.|\:|\-)\s*([^\n]+)',
        r'whether\s+([^.]+\.)',
        r'the\s+question\s+(?:for\s+)?(?:consideration\s+)?(?:is|are)\s*(?:whether\s+)?([^.]+\.)',
        r'point[s]?\s*(?:for\s+)?(?:determination|consideration)\s*(?:' + _D_PLUS + r'\.|\:|\-)\s*([^\n]+)',
    ]

    for pattern in issue_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            issue_text = match.group(1).strip()
            if len(issue_text) > 20 and issue_text not in [i['issue'] for i in issues]:
                issues.append({
                    "issue": issue_text[0].upper() + issue_text[1:],
                    "type": "explicit"
                })

    # Pattern 2: Infer issues from "contention" or "submission"
    contention_pattern = r'(?:the\s+)?(?:petitioner|appellant|respondent|defendant|plaintiff)[\'"]?s?\s+(?:main|primary|key)?\s*(?:contention|submission|argument)\s*(?:is|was|that)\s*([^.]+\.)'
    matches = re.finditer(contention_pattern, text_lower, re.IGNORECASE)
    for match in matches:
        issue_text = match.group(1).strip()
        if len(issue_text) > 20 and issue_text not in [i['issue'] for i in issues]:
            issues.append({
                "issue": issue_text[0].upper() + issue_text[1:],
                "type": "inferred"
            })

    return issues[:5]  # Limit to top 5 issues


def extract_timeline(text: str) -> list[dict]:
    """
    Extract dates and events to build a case timeline.
    Returns chronological list of {date, event} pairs.
    """
    if not text:
        return []

    from datetime import datetime

    timeline = []

    # Date patterns (Indian and international formats)
    _sep = r'[/\-]'
    _months = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    
    date_patterns = [
        # DD/MM/YYYY or DD-MM-YYYY
        _D_1_2 + _sep + _D_1_2 + _sep + _D_4,
        # DD Month YYYY (e.g., 15 January 2023)
        _D_1_2 + _SP + _months + _SP + _D_4,
        # Month DD, YYYY (e.g., January 15, 2023)
        _months + _SP + _D_1_2 + r',?' + _SP + _D_4,
        # YYYY-MM-DD
        _D_4 + _sep + _D_1_2 + _sep + _D_1_2,
    ]

    month_map = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    def parse_date(date_str):
        """Parse various date formats to datetime object."""
        date_str = date_str.strip()
        _sep = r'[/\-]'
        _word = r'(\w+)'

        # DD/MM/YYYY or DD-MM-YYYY
        match = re.match(_D_1_2 + _sep + _D_1_2 + _sep + _D_4, date_str)
        if match:
            return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))

        # DD Month YYYY
        match = re.match(_D_1_2 + _SP + _word + _SP + _D_4, date_str, re.IGNORECASE)
        if match and match.group(2).lower() in month_map:
            return datetime(int(match.group(3)), month_map[match.group(2).lower()], int(match.group(1)))

        # Month DD, YYYY
        match = re.match(_word + _SP + _D_1_2 + r',?' + _SP + _D_4, date_str, re.IGNORECASE)
        if match and match.group(1).lower() in month_map:
            return datetime(int(match.group(3)), month_map[match.group(1).lower()], int(match.group(2)))

        # YYYY-MM-DD
        match = re.match(_D_4 + _sep + _D_1_2 + _sep + _D_1_2, date_str)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))

        return None

    # Extract dates with surrounding context
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_str = match.group(1)
            parsed_date = parse_date(date_str)

            if parsed_date:
                # Get surrounding text as event description
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                context = text[start:end]

                # Clean up context
                context = re.sub(r'\s+', ' ', context).strip()
                if len(context) > 150:
                    context = context[:150] + '...'

                # Avoid duplicates
                if parsed_date not in [t['date_obj'] for t in timeline]:
                    timeline.append({
                        "date": parsed_date.strftime("%d %B %Y"),
                        "date_obj": parsed_date,
                        "event": context,
                        "raw_date": date_str
                    })

    # Sort by date
    timeline.sort(key=lambda x: x['date_obj'])

    # Remove date_obj for final output
    for t in timeline:
        del t['date_obj']

    return timeline[:15]  # Limit to 15 events


def extract_monetary_claims(text: str) -> list[dict]:
    """
    Extract all monetary amounts mentioned in a legal document.
    Returns list of {amount, context, type} objects.
    """
    if not text:
        return []

    amounts = []
    seen_amounts = set()

    # Patterns for Indian currency (₹, Rs., Rupees)
    _m_dec = r'(?:\.' + _D + r'{2})?'
    money_patterns = [
        # ₹50,000 or ₹ 50,000
        r'₹\s*([' + _D + r',]+' + _m_dec + r')',
        # Rs. 50,000 or Rs 50,000
        r'Rs\.?\s*([' + _D + r',]+' + _m_dec + r')',
        # Rupees 50,000
        r'Rupees\s*([' + _D + r',]+' + _m_dec + r')',
        # INR 50,000
        r'INR\s*([' + _D + r',]+' + _m_dec + r')',
        # Fifty thousand rupees (word form - basic)
        r'((?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakh|crore|\s)+)\s*rupees?',
    ]

    # Context keywords to classify the type of amount
    type_keywords = {
        'bribe': ['bribe', 'bribery', 'illegal gratification', 'illegal payment'],
        'fine': ['fine', 'penalty', 'penalized'],
        'compensation': ['compensation', 'damages', 'award', 'awarded'],
        'disputed': ['disputed', 'claim', 'claimed', 'dispute'],
        'salary': ['salary', 'wages', 'remuneration', 'emolument'],
        'recovery': ['recovery', 'recovered', 'restitution'],
    }

    for pattern in money_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            raw_amount = match.group(1).strip() if match.lastindex else match.group(0)

            # Convert word form to numeric (simplified)
            if raw_amount.replace(' ', '').replace('lakh', '').replace('crore', '').replace('thousand', '').isalpha():
                # Skip word-form amounts for now (complex to parse)
                continue

            # Clean numeric amount
            clean_amount = raw_amount.replace(',', '')
            try:
                numeric = float(clean_amount)
            except ValueError:
                continue

            # Format nicely
            formatted = f"₹{int(numeric):,}" if numeric == int(numeric) else f"₹{numeric:,.2f}"

            # Determine context/type
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 50)
            context = text[start:end].lower()

            amount_type = 'amount'
            for atype, keywords in type_keywords.items():
                if any(kw in context for kw in keywords):
                    amount_type = atype
                    break

            # Avoid duplicates
            if formatted not in seen_amounts:
                seen_amounts.add(formatted)
                amounts.append({
                    "amount": formatted,
                    "numeric": numeric,
                    "type": amount_type,
                    "context": text[start:end].strip()[:100]
                })

    # Sort by amount (descending)
    amounts.sort(key=lambda x: x['numeric'], reverse=True)

    return amounts[:10]


def extract_section_wise_summary(text: str) -> dict:
    """
    Break down a legal document into structured sections:
    - Facts: What happened
    - Issues: Legal questions
    - Arguments: Contentions from both sides
    - Reasoning: Court's analysis
    - Order: Final judgment
    """
    if not text or len(text.strip()) < 200:
        return {}

    sections = {
        "facts": "",
        "issues": "",
        "petitioner_arguments": "",
        "respondent_arguments": "",
        "reasoning": "",
        "order": ""
    }

    text_lower = text.lower()

    # Extract facts (usually early in the document)
    facts_markers = ['brief facts', 'background', 'factual background', 'case background', 'the facts', 'facts of the case']
    for marker in facts_markers:
        if marker in text_lower:
            start = text_lower.find(marker)
            # Get text until next section marker
            end_markers = ['issue', 'question', 'contention', 'submission', 'argument', 'hearing', 'order']
            end = len(text)
            for em in end_markers:
                pos = text_lower.find(em, start + len(marker))
                if pos != -1 and pos < end:
                    end = pos
            sections["facts"] = text[start:end].strip()
            break

    # Extract issues
    issues_markers = ['issues', 'questions for consideration', 'points for determination', 'legal issues']
    for marker in issues_markers:
        if marker in text_lower:
            start = text_lower.find(marker)
            end = len(text)
            for em in ['contention', 'submission', 'argument', 'hearing', 'order', 'reasoning']:
                pos = text_lower.find(em, start + len(marker))
                if pos != -1 and pos < end:
                    end = pos
            sections["issues"] = text[start:end].strip()
            break

    # Extract arguments
    petitioner_markers = ['petitioner', 'appellant', 'plaintiff']
    respondent_markers = ['respondent', 'defendant', 'opposite party']

    for marker in petitioner_markers:
        if f'{marker}s' in text_lower or f'{marker} contentions' in text_lower or f'{marker} submissions' in text_lower:
            # Find the contentions/submissions section
            for sub_marker in ['contention', 'submission', 'argument']:
                pattern = f'{marker}[\'"]?s?\\s+{sub_marker}'
                match = re.search(pattern, text_lower)
                if match:
                    start = match.start()
                    end = min(text_lower.find('respondent', start), text_lower.find('court', start), text_lower.find('order', start))
                    if end == -1:
                        end = start + 500
                    sections["petitioner_arguments"] = text[start:end].strip()
                    break
            break

    for marker in respondent_markers:
        if f'{marker}s' in text_lower or f'{marker} contentions' in text_lower or f'{marker} submissions' in text_lower:
            for sub_marker in ['contention', 'submission', 'argument']:
                pattern = f'{marker}[\'"]?s?\\s+{sub_marker}'
                match = re.search(pattern, text_lower)
                if match:
                    start = match.start()
                    end = min(text_lower.find('court', start), text_lower.find('order', start), text_lower.find('reasoning', start))
                    if end == -1:
                        end = start + 500
                    sections["respondent_arguments"] = text[start:end].strip()
                    break
            break

    # Extract reasoning
    reasoning_markers = ['reasoning', 'analysis', 'court\'s analysis', 'discussion', 'consideration']
    for marker in reasoning_markers:
        if marker in text_lower:
            start = text_lower.find(marker)
            end = text_lower.find('order', start)
            if end == -1:
                end = start + 800
            sections["reasoning"] = text[start:end].strip()
            break

    # Extract order
    order_markers = ['order', 'judgment', 'decree', 'directions', 'disposed of', 'allowed', 'dismissed']
    for marker in order_markers:
        if marker in text_lower:
            start = text_lower.rfind(marker)  # Use rfind for last occurrence
            sections["order"] = text[start:start+500].strip()
            break

    # Clean up empty sections
    sections = {k: v for k, v in sections.items() if v}

    return sections


def analyze_legal_document(text: str) -> dict:
    """
    Comprehensive legal document analysis.
    Combines all extraction functions into one call.
    """
    return {
        "case_type": classify_case_type(text),
        "legal_issues": extract_legal_issues(text),
        "timeline": extract_timeline(text),
        "monetary_claims": extract_monetary_claims(text),
        "sections": extract_section_wise_summary(text),
        "citations": extract_citations(text)
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
