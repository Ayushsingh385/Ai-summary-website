"""
Difference Engine — Semantic document comparison for Zilla Parishad administrative documents.

Specifically designed for:
- Land disputes
- Government scheme records
- Administrative documents
- Semi-structured bureaucratic text

Key Features:
- Normalizes names, dates, numbers, plot IDs to placeholders
- Handles repetitive bureaucratic language with small variations
- Adjusted thresholds for administrative document similarity
- Comprehensive debug output

Classification thresholds (adjusted for this domain):
    - similarity >= 0.85 -> Identical (or near-identical structure)
    - 0.65 <= similarity < 0.85 -> Modified
    - similarity < 0.65 -> Different
"""

import re
import logging
from typing import Optional, List, Tuple, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

DEBUG_MODE = False

# Thresholds adjusted for administrative/legal documents
# These documents have more structural similarity, so thresholds are slightly lowered
THRESHOLD_IDENTICAL = 0.85  # User requirement: >= 0.85 -> Identical
THRESHOLD_MODIFIED = 0.65   # User requirement: 0.65-0.85 -> Modified

MIN_SEGMENT_LENGTH = 20  # Slightly higher to avoid fragments

# Model singleton
_embedding_model = None
_model_load_attempted = False


# ──────────────────────────────────────────────────────────────
# Entity Normalization Patterns
# ──────────────────────────────────────────────────────────────

# Patterns for normalizing entity variations
ENTITY_PATTERNS = {
    # Indian names (common in Zilla Parishad docs)
    "names": [
        # Full names: "Shri Ram Kumar", "Smt. Priya Sharma"
        (r'\b(?:Shri|Smt|Shrimati|Kumar|Kumari|Dr|Late)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', '<NAME>'),
        # Names with titles: "Ram Kumar s/o Hari Kumar"
        (r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:s/o|d/o|w/o|son of|daughter of|wife of)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', '<NAME>'),
        # Simple names: "Ram", "Shyam" (capitalized words that look like names)
        # Exclude common bureaucratic words
        (r'\b(?!(?:Plot|Gat|Survey|The|As|Per|Case|Application|Village|Taluka|District|Ahmednagar|Rahuri|Sangamner|Seven|Twelve|NOC)\b)[A-Z][a-z]{2,15}\b(?=\s+(?:s/o|d/o|w/o|son of|daughter of|wife of|resident|of|,|\.)?)', '<NAME>'),
    ],
    # Plot/Property numbers
    "plot_numbers": [
        # Survey numbers: "Survey No. 123", "S.No. 45/2"
        (r'\b(?:Survey|Sur\.?|S\.?\s*No\.?)\s*(?:Number|No\.?)?\s*[:#]?\s*\d+(?:/\d+)?(?:-\d+)?\b', '<PLOT>'),
        # Plot numbers: "Plot No. 123", "Plot 45A"
        (r'\b(?:Plot|Gat)\s*(?:No\.?)?\s*[:#]?\s*\d+(?:/\d+)?(?:[A-Z])?\b', '<PLOT>'),
        # Khasra numbers: "Khasra No. 123"
        (r'\b(?:Khasra|Khasra)\s*(?:No\.?)?\s*[:#]?\s*\d+(?:/\d+)?\b', '<PLOT>'),
        # Gat numbers (Maharashtra land records)
        (r'\bGat\s*(?:No\.?)?\s*[:#]?\s*\d+(?:/\d+)?\b', '<PLOT>'),
    ],
    # Case/Reference numbers
    "case_numbers": [
        # Case numbers: "Case No. 123/2024", "Application No. 456"
        (r'\b(?:Case|Application|Petition|Appeal|Reference|File)\s*(?:No\.?)?\s*[:#]?\s*\d+(?:/\d+)?(?:/\d{2,4})?\b', '<CASE>'),
        # Registration numbers
        (r'\b(?:Reg(?:istration)?|Registration)\s*(?:No\.?)?\s*[:#]?\s*\d+(?:/\d+)?(?:/\d{2,4})?\b', '<CASE>'),
    ],
    # Dates
    "dates": [
        # Indian date format: "12/05/2024", "12-05-2024"
        (r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', '<DATE>'),
        # Written dates: "12th May, 2024", "May 12, 2024"
        (r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,?\s*\d{2,4}\b', '<DATE>'),
        # Reverse written dates: "May 12, 2024"
        (r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}\b', '<DATE>'),
        # Year alone in context: "year 2024" -> keep years for now
    ],
    # Monetary amounts
    "money": [
        # Rs. amounts: "Rs. 50,000", "Rs. 5 Lakh"
        (r'\b(?:Rs\.?|INR)\s*\.?\s*\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:Lakh|Lakhs|Thousand|Crore))?\b', '<AMOUNT>'),
        (r'\b\d+(?:,\d+)*(?:\.\d+)?\s*(?:Rupees|Rs\.?)\b', '<AMOUNT>'),
    ],
    # Land measurements
    "measurements": [
        # Area: "5 Acres", "2.5 Hectares", "100 sq.m."
        (r'\b\d+(?:\.\d+)?\s*(?:Acres?|Hectares?|Are|Sq\.?\s*Metr?e?s?|Sq\.?\s*ft\.?|Square\s+(?:Feet|Meter|Metres))\b', '<AREA>'),
        # Guntha (Maharashtra land unit)
        (r'\b\d+(?:\.\d+)?\s*(?:Guntha|Gunthe)\b', '<AREA>'),
    ],
    # Village/Location identifiers
    "locations": [
        # Village: "Village XYZ", "Gram Panchayat ABC"
        (r'\b(?:Village|Gram|Grampanchayat|Gram\s+Panchayat)\s+[A-Z][a-zA-Z]+', '<VILLAGE>'),
        # District/Taluka: "Taluka ABC", "District XYZ"
        (r'\b(?:Taluka|Tehsil|Taluk|District)\s+[A-Z][a-zA-Z]+', '<LOCATION>'),
    ],
    # Document identifiers
    "documents": [
        # 7/12 extract, 8A, etc.
        (r'\b(?:Seven Twelve|7\s*/\s*12|Satbara|8\s*A)\s*(?:Extract|Utara)?\b', '<DOC>'),
        # Property card
        (r'\b(?:Property\s+Card|Ferfar)\b', '<DOC>'),
    ],
    # Catch-all for other IDs/Numbers (e.g., specific case numbers or land IDs)
    "generic_ids": [
        (r'\b\d{3,10}\b', '<ID>'),  # Any 3-10 digit number is likely a non-meaningful ID in this context
    ]
}

# Compile all patterns into a single normalization pass
COMPILED_PATTERNS = []
for category, patterns in ENTITY_PATTERNS.items():
    for pattern, replacement in patterns:
        COMPILED_PATTERNS.append((re.compile(pattern, re.IGNORECASE), replacement))


def normalize_text(text: str) -> str:
    """
    Normalize document text by replacing entity variations with placeholders.
    This allows semantic comparison of structure rather than exact content.

    Example:
        Input:  "Plot 123 owned by Ram Kumar s/o Hari Kumar"
        Output: "<PLOT> owned by <NAME> s/o <NAME>"

    This normalization preserves the STRUCTURE while ignoring specific values.
    """
    normalized = text

    for pattern, replacement in COMPILED_PATTERNS:
        normalized = pattern.sub(replacement, normalized)

    # Normalize multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized


def create_comparison_pair(original: str, normalized: str) -> dict:
    """Create a pair showing original and normalized text for debugging."""
    return {"original": original, "normalized": normalized}


# ──────────────────────────────────────────────────────────────
# Model Loading
# ──────────────────────────────────────────────────────────────

def _get_embedding_model():
    """
    Load the sentence-transformers model (lazy singleton).
    """
    global _embedding_model, _model_load_attempted

    if _model_load_attempted:
        return _embedding_model

    _model_load_attempted = True

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 model...")
        _embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully.")
    except Exception as exc:
        logger.error("Failed to load embedding model: %s", exc)
        _embedding_model = None
        raise

    return _embedding_model


# ──────────────────────────────────────────────────────────────
# Text Segmentation
# ──────────────────────────────────────────────────────────────

def _split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using multiple methods.
    Handles: numbered clauses, legal paragraphs, bureaucratic text.
    """
    if not text or not text.strip():
        return []

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'\n+', ' ', text)

    sentences = []

    # Method 1: Split on sentence-ending punctuation
    # Handles: . ! ? followed by space and capital letter or number
    raw_splits = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)

    for segment in raw_splits:
        segment = segment.strip()
        if not segment:
            continue

        # Method 2: Handle numbered clauses within segments
        # Pattern: "1. First point 2. Second point 3. Third point"
        clause_pattern = r'(?<=\.)\s*(?=\d+[\.\)]\s+[A-Z])'
        potential_clauses = re.split(clause_pattern, segment)

        if len(potential_clauses) > 1:
            # Found numbered clauses
            for clause in potential_clauses:
                clause = clause.strip()
                # Clean leading number if present
                clause = re.sub(r'^\d+[\.\)]\s*', '', clause).strip()
                if len(clause) >= MIN_SEGMENT_LENGTH:
                    sentences.append(clause)
        else:
            if len(segment) >= MIN_SEGMENT_LENGTH:
                sentences.append(segment)

    # Clean up: ensure sentences are meaningful
    cleaned = []
    for s in sentences:
        # Remove leading numbers/punctuation
        s = re.sub(r'^[\d\.\)\-\:]+\s*', '', s).strip()
        if len(s) >= MIN_SEGMENT_LENGTH:
            cleaned.append(s)

    return cleaned


# ──────────────────────────────────────────────────────────────
# Embedding & Similarity
# ──────────────────────────────────────────────────────────────

def _encode_segments(segments: List[str], model, use_normalization: bool = True) -> Tuple[np.ndarray, List[str]]:
    """
    Generate embeddings for segments.
    Returns (embeddings, normalized_texts).
    """
    if not segments:
        return np.array([]), []

    # Normalize text for embedding (replaces entities with placeholders)
    if use_normalization:
        normalized_texts = [normalize_text(s) for s in segments]
    else:
        normalized_texts = [s.lower().strip() for s in segments]

    # Generate embeddings with L2 normalization for cosine similarity
    embeddings = model.encode(
        normalized_texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=True
    )

    if DEBUG_MODE:
        logger.info(f"Encoded {len(segments)} segments")
        # Verify embeddings are valid
        norms = np.linalg.norm(embeddings, axis=1)
        zero_norms = np.sum(norms < 0.1)
        if zero_norms > 0:
            logger.warning(f"Found {zero_norms} near-zero embeddings!")

    return embeddings, normalized_texts


def _compute_similarity_matrix(embeddings_a: np.ndarray, embeddings_b: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity matrix between two embedding sets.
    """
    if embeddings_a.size == 0 or embeddings_b.size == 0:
        return np.array([])

    # Cosine similarity (embeddings are already L2-normalized)
    similarity_matrix = cosine_similarity(embeddings_a, embeddings_b)

    # Clamp to [0, 1] (negative cosine is rare but possible)
    similarity_matrix = np.clip(similarity_matrix, 0, 1)

    return similarity_matrix


# ──────────────────────────────────────────────────────────────
# Debug Output
# ──────────────────────────────────────────────────────────────

def _debug_print_sample_segments(segments_a: List[str], segments_b: List[str],
                                  norm_a: List[str], norm_b: List[str]):
    """Print sample of cleaned/normalized segments."""
    if not DEBUG_MODE:
        return

    print("\n" + "=" * 80)
    print("SAMPLE SEGMENTS (after normalization)")
    print("=" * 80)

    print(f"\nDocument A - {len(segments_a)} segments:")
    for i in range(min(3, len(segments_a))):
        print(f"\n  [{i}] ORIGINAL:")
        print(f"      {segments_a[i][:100]}...")
        print(f"      NORMALIZED:")
        print(f"      {norm_a[i][:100]}...")

    print(f"\nDocument B - {len(segments_b)} segments:")
    for i in range(min(3, len(segments_b))):
        print(f"\n  [{i}] ORIGINAL:")
        print(f"      {segments_b[i][:100]}...")
        print(f"      NORMALIZED:")
        print(f"      {norm_b[i][:100]}...")


def _debug_print_similarity_matrix(sim_matrix: np.ndarray, norm_a: List[str], norm_b: List[str]):
    """Print similarity matrix for debugging."""
    if not DEBUG_MODE:
        return

    print("\n" + "=" * 80)
    print("SIMILARITY MATRIX (cosine similarity between normalized segments)")
    print("=" * 80)

    # Print header
    print(f"\n{'':40}", end="")
    for j in range(min(5, len(norm_b))):
        short_b = norm_b[j][:30] + "..." if len(norm_b[j]) > 30 else norm_b[j]
        print(f"B[{j}]:{short_b:<15}", end="")
    print()

    # Print rows
    for i in range(min(10, len(norm_a))):
        short_a = norm_a[i][:35] + "..." if len(norm_a[i]) > 35 else norm_a[i]
        print(f"A[{i}]: {short_a:<35}", end="")
        for j in range(min(5, len(norm_b))):
            print(f"  {sim_matrix[i,j]:.3f}      ", end="")
        print()

    print("\n" + "=" * 80)


def _debug_print_matches(matches: List[dict]):
    """Print match details for debugging."""
    if not DEBUG_MODE:
        return

    print("\n" + "=" * 80)
    print("MATCH RESULTS (A -> best match in B)")
    print("=" * 80)

    for match in matches:
        sim = match["similarity"]
        if sim >= THRESHOLD_IDENTICAL:
            status = "IDENTICAL"
        elif sim >= THRESHOLD_MODIFIED:
            status = "MODIFIED"
        else:
            status = "DIFFERENT"

        print(f"\n[{status}] Similarity: {sim:.4f}")
        print(f"  A (original): {match['segment_a_original'][:120]}")
        print(f"  A (cleaned):  {match['segment_a_normalized'][:120]}")
        print(f"  B (original): {match['segment_b_original'][:120]}")
        print(f"  B (cleaned):  {match['segment_b_normalized'][:120]}")

    print("=" * 80 + "\n")


# ──────────────────────────────────────────────────────────────
# Matching Logic
# ──────────────────────────────────────────────────────────────

def _find_best_matches(
    sim_matrix: np.ndarray,
    segments_a: List[str],
    segments_b: List[str],
    norm_a: List[str],
    norm_b: List[str]
) -> List[dict]:
    """
    Find best matching segment in B for each segment in A.
    Includes both original and normalized text in results.
    """
    matches = []

    if sim_matrix.size == 0:
        return matches

    for i, seg_a in enumerate(segments_a):
        # Find best match in B
        best_idx = int(np.argmax(sim_matrix[i]))
        best_score = float(sim_matrix[i, best_idx])
        best_match_b = segments_b[best_idx]

        matches.append({
            "segment_a": seg_a,
            "segment_a_original": seg_a,
            "segment_a_normalized": norm_a[i],
            "best_match_b": best_match_b,
            "segment_b_original": best_match_b,
            "segment_b_normalized": norm_b[best_idx],
            "match_index": best_idx,
            "similarity": round(best_score, 4)
        })

    return matches


def _classify_segments(
    matches_a: List[dict],
    matches_b: List[dict]
) -> dict:
    """
    Classify segments into identical, modified, added, and removed.
    """
    identical = []
    modified = []
    matched_b_indices = set()

    # Process A -> B matches
    for match in matches_a:
        similarity = match["similarity"]

        if similarity >= THRESHOLD_IDENTICAL:
            identical.append(match["segment_a_original"])
            matched_b_indices.add(match["match_index"])
        elif similarity >= THRESHOLD_MODIFIED:
            modified.append({
                "original": match["segment_a_original"],
                "original_normalized": match["segment_a_normalized"],
                "updated": match["segment_b_original"],
                "updated_normalized": match["segment_b_normalized"],
                "similarity": similarity
            })
            matched_b_indices.add(match["match_index"])

    # Find removed segments (in A, no good match in B)
    removed = []
    for match in matches_a:
        if match["similarity"] < THRESHOLD_MODIFIED:
            removed.append(match["segment_a_original"])

    # Find added segments (in B, no good match in A)
    added = []
    for match in matches_b:
        if match["similarity"] < THRESHOLD_MODIFIED:
            added.append(match["segment_b_original"])

    # Final Deduplication & Cross-Exclusion
    # (Using dict.fromkeys to preserve order while removing duplicates)
    identical = list(dict.fromkeys(identical))
    removed = list(dict.fromkeys(removed))
    added = list(dict.fromkeys(added))
    
    # Strictly ensure something shown as identical is not in added/removed
    removed = [r for r in removed if r not in identical]
    added = [a for a in added if a not in identical]

    return {
        "identical": identical,
        "modified": modified,
        "added": added,
        "removed": removed
    }


# ──────────────────────────────────────────────────────────────
# Main Public API
# ──────────────────────────────────────────────────────────────

def compare_documents_semantic(
    doc_a: str,
    doc_b: str,
    debug: bool = False
) -> dict:
    """
    Compare two Zilla Parishad/administrative documents using semantic embeddings.
    Returns enriched JSON for the frontend with specific lines and topics.
    """
    global DEBUG_MODE
    if debug:
        DEBUG_MODE = True

    # Load model
    model = _get_embedding_model()
    if model is None:
        raise RuntimeError("Embedding model not available.")

    # Step 1: Split documents into segments
    raw_segments_a = _split_into_sentences(doc_a)
    raw_segments_b = _split_into_sentences(doc_b)

    # Handle empty documents
    if not raw_segments_a and not raw_segments_b:
        return _empty_result()

    # Step 2: Generate embeddings
    embeddings_a, norm_a = _encode_segments(raw_segments_a, model)
    embeddings_b, norm_b = _encode_segments(raw_segments_b, model)

    # Step 3: Compute similarity matrix
    sim_matrix = _compute_similarity_matrix(embeddings_a, embeddings_b)

    # Step 4: Find best matches
    matches_a = _find_best_matches(sim_matrix, raw_segments_a, raw_segments_b, norm_a, norm_b)
    sim_matrix_reverse = _compute_similarity_matrix(embeddings_b, embeddings_a)
    matches_b = _find_best_matches(sim_matrix_reverse, raw_segments_b, raw_segments_a, norm_b, norm_a)

    # Step 5: Classify segments
    classification = _classify_segments(matches_a, matches_b)

    # ──────────────────────────────────────────────────────────────
    # NEW: Enriching for Frontend with Progressive Exclusion
    # ──────────────────────────────────────────────────────────────
    
    # Visibility Registry: Tracks all text already "shown" to avoid repetition
    shown_registry = set()
    
    # 1. Primary Sections (Full Clauses/Blocks)
    shared_blocks = classification["identical"]
    for s in shared_blocks: shown_registry.add(s)

    # Modified Clauses
    modified_items = []
    if classification["modified"]:
        for m in classification["modified"]:
            text = f"Revised: {m['updated']} (Previously: {m['original']})"
            modified_items.append(text)
            shown_registry.add(m['updated'])
            shown_registry.add(m['original'])

    # Unique Clauses (Added/Removed)
    removed_clauses = classification["removed"]
    added_clauses = classification["added"]
    for c in removed_clauses: shown_registry.add(c)
    for c in added_clauses: shown_registry.add(c)

    def is_in_segments(item: str) -> bool:
        """Helper to check if item is in any classified segment (unused for entities now)."""
        item_lower = item.lower()
        for shown in shown_registry:
            if item_lower in shown.lower():
                return True
        return False

    # 2. Similarities (Entities)
    similarities = []
    ents_a = _extract_domain_entities(doc_a)
    ents_b = _extract_domain_entities(doc_b)
    
    # Track entities to filter topics later
    all_identified_entities = set()

    for etype, label in [
        ("plot_numbers", "Land / Plot IDs"),
        ("names", "Persons / Parties"),
        ("dates", "Dates"),
        ("money", "Monetary Values"),
        ("locations", "Villages / Talukas"),
        ("documents", "Document Types")
    ]:
        set_a = set(ents_a.get(etype, []))
        set_b = set(ents_b.get(etype, []))
        shared = sorted(list(set_a & set_b))
        
        # RESTORED: Don't filter entities against sentences anymore
        if shared:
            similarities.append({"category": label, "items": shared})
            for s in shared: all_identified_entities.add(s.lower())

    if modified_items:
        similarities.append({"category": "Legal Clauses (Modified)", "items": modified_items})

    # 3. Differences (Unique Entities)
    differences = []
    for etype, label in [
        ("plot_numbers", "Land / Plot IDs"),
        ("names", "Persons / Parties"),
        ("dates", "Dates"),
        ("money", "Monetary Values"),
        ("locations", "Villages / Talukas")
    ]:
        set_a = set(ents_a.get(etype, []))
        set_b = set(ents_b.get(etype, []))
        only_a = sorted(list(set_a - set_b))
        only_b = sorted(list(set_b - set_a))
        
        # RESTORED: Don't filter entities against sentences
        if only_a or only_b:
            differences.append({
                "category": label,
                "only_in_doc1": only_a,
                "only_in_doc2": only_b
            })
            for item in only_a + only_b: all_identified_entities.add(item.lower())

    if removed_clauses or added_clauses:
        differences.append({
            "category": "Unique Clauses (Document Specific)",
            "only_in_doc1": removed_clauses,
            "only_in_doc2": added_clauses
        })

    # 4. Topics (Keywords)
    topics_a = _get_keywords_simple(doc_a)
    topics_b = _get_keywords_simple(doc_b)
    
    def is_entity_overlap(word: str) -> bool:
        """Check if a topic word is already part of an identified entity."""
        word_lower = word.lower()
        for ent in all_identified_entities:
            if word_lower in ent:
                return True
        return False

    # Filter topics ONLY against entities (to avoid "Ram" separately from "Shri Ram")
    # Stop filtering topics against full segments to restore visibility
    shared_topics = [t for t in sorted(list(set(topics_a) & set(topics_b))) if not is_entity_overlap(t)]
    unique_topics_1 = [t for t in sorted(list(set(topics_a) - set(topics_b))) if not is_entity_overlap(t)]
    unique_topics_2 = [t for t in sorted(list(set(topics_b) - set(topics_a))) if not is_entity_overlap(t)]

    # 5. Build Final Result
    result = {
        "identical": classification["identical"],
        "modified": classification["modified"],
        "added": classification["added"],
        "removed": classification["removed"],
        "shared_blocks": shared_blocks,
        "similarities": similarities,
        "differences": differences,
        "shared_topics": shared_topics,
        "unique_topics_doc1": unique_topics_1,
        "unique_topics_doc2": unique_topics_2,
        "stats": {
            "total_segments_a": len(raw_segments_a),
            "total_segments_b": len(raw_segments_b),
            "identical_count": len(classification["identical"]),
            "modified_count": len(classification["modified"]),
            "added_count": len(classification["added"]),
            "removed_count": len(classification["removed"]),
        }
    }

    # Debug info
    if debug:
        result["debug_info"] = {
            "sample_similarity_scores": [m["similarity"] for m in matches_a[:5]],
            "entities_a": ents_a,
            "entities_b": ents_b,
            "registry_size": len(shown_registry)
        }

    return result


def _extract_domain_entities(text: str) -> Dict[str, List[str]]:
    """Extract entities grouped by domain category using ENTITY_PATTERNS."""
    found = {}
    
    # Words to exclude from "Persons / Parties"
    NAME_BLACK_LIST = {
        "shri", "smt", "shrimati", "kumar", "kumari", "the", "land", "owned", 
        "application", "survey", "plot", "gat", "was", "for", "conducted",
        "conversion", "submitted", "property", "shows", "encumbrances",
        "extract", "seven", "twelve", "clear", "as", "per", "from", "with"
    }

    for category, patterns in ENTITY_PATTERNS.items():
        if category == "generic_ids": continue
        items = []
        for pattern_str, _ in patterns:
            # ONLY use IGNORECASE for non-name patterns
            # Names should preserve capitalization to avoid common word noise
            flags = re.IGNORECASE if category != "names" else 0
            
            matches = re.finditer(pattern_str, text, flags)
            for match in matches:
                m = match.group().strip()
                
                # Cleanup and Filtering for Names
                if category == "names":
                    # Remove trailing punctuation
                    m = re.sub(r'[,\.]$', '', m).strip()
                    
                    # 1. Skip if it's just a standalone title
                    if m.lower() in ["shri", "smt", "shrimati", "dr", "late"]:
                        continue
                        
                    # 2. Skip if in black list
                    if m.lower() in NAME_BLACK_LIST:
                        continue
                        
                    # 3. Skip if too short (likely noise)
                    if len(m) < 3:
                        continue
                        
                    # 4. If it's a multi-word name, remove prefix title for normalization comparison
                    # but keep it for display if it's part of a larger name
                
                if m not in items:
                    items.append(m)
        
        # FINAL CLEANUP for names: Deduplicate and remove subsets (e.g. if "Shri Ram" exists, remove "Ram")
        if category == "names" and items:
            # Sort by length descending to catch longer names first
            items.sort(key=len, reverse=True)
            deduped = []
            for i, name in enumerate(items):
                is_subset = False
                for other in deduped:
                    if name in other:
                        is_subset = True
                        break
                if not is_subset:
                    deduped.append(name)
            items = sorted(deduped)

        found[category] = items
    return found


def _get_keywords_simple(text: str, top_n: int = 15) -> List[str]:
    """Helper for simple keyword extraction."""
    stop_words = {"the", "and", "under", "this", "that", "from", "with", "were", "been"}
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    freq = {}
    for w in words:
        if w not in stop_words:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, f in sorted_words[:top_n]]


def _empty_result(**kwargs) -> dict:
    """Create an empty result dict with optional overrides."""
    result = {
        "identical": [],
        "modified": [],
        "added": [],
        "removed": [],
        "stats": {
            "total_segments_a": 0,
            "total_segments_b": 0,
            "identical_count": 0,
            "modified_count": 0,
            "added_count": 0,
            "removed_count": 0
        }
    }
    for key, value in kwargs.items():
        if key == "stats":
            result["stats"].update(value)
        else:
            result[key] = value
    return result


# ──────────────────────────────────────────────────────────────
# Summary Generation
# ──────────────────────────────────────────────────────────────

def get_comparison_summary(result: dict) -> str:
    """Generate a human-readable summary of comparison results."""
    stats = result.get("stats", {})

    lines = [
        "Document Comparison Summary",
        "=" * 40,
        f"Document A: {stats.get('total_segments_a', 0)} segments",
        f"Document B: {stats.get('total_segments_b', 0)} segments",
        "",
        f"Identical: {stats.get('identical_count', 0)} ({stats.get('thresholds', {}).get('identical', 0.85):.0%}+ similarity)",
        f"Modified: {stats.get('modified_count', 0)} ({stats.get('thresholds', {}).get('modified', 0.65):.0%}-{stats.get('thresholds', {}).get('identical', 0.85):.0%} similarity)",
        f"Added: {stats.get('added_count', 0)} (new in B)",
        f"Removed: {stats.get('removed_count', 0)} (missing from B)",
    ]

    if result.get("modified"):
        lines.append("")
        lines.append("Modified segments (sample):")
        for m in result["modified"][:3]:
            lines.append(f"  - Similarity: {m['similarity']:.1%}")
            lines.append(f"    Original: {m['original'][:60]}...")
            lines.append(f"    Updated:  {m['updated'][:60]}...")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Test Function
# ──────────────────────────────────────────────────────────────

def test_comparison():
    """
    Test with Zilla Parishad-style documents.
    """
    # Simulated Zilla Parishad land dispute document A
    doc_a = """
    Plot No. 123, Gat No. 45, Village Rahuri, Taluka Rahuri, District Ahmednagar.
    The land measuring 5 Acres 20 Gunthas is owned by Shri Ram Kumar s/o Hari Kumar.
    As per 7/12 Extract, the land is classified as agricultural land.
    The current market value is estimated at Rs. 15,00,000.
    Application No. 456/2024 was submitted on 12/05/2024 for land conversion.
    The Gram Panchayat has given NOC for the said land on 20/06/2024.
    """

    # Similar document B with small variations (names, numbers changed)
    doc_b = """
    Plot No. 456, Gat No. 78, Village Sangamner, Taluka Sangamner, District Ahmednagar.
    The land measuring 3 Acres 15 Gunthas is owned by Shri Shyam Patil s/o Ganesh Patil.
    As per 7/12 Extract, the land is classified as agricultural land.
    The current market value is estimated at Rs. 12,50,000.
    Application No. 789/2024 was submitted on 25/07/2024 for land conversion.
    The Gram Panchayat has given NOC for the said land on 15/08/2024.
    An additional survey was conducted on 01/09/2024.
    """

    print("\n" + "=" * 80)
    print("TESTING WITH ZILLA PARISHAD-STYLE DOCUMENTS")
    print("=" * 80)
    print("\n[Document A - Key entities]")
    print("  Plot: 123, Gat: 45, Village: Rahuri, Owner: Ram Kumar s/o Hari Kumar")
    print("  Area: 5 Acres 20 Gunthas, Value: Rs. 15,00,000")
    print("\n[Document B - Key entities]")
    print("  Plot: 456, Gat: 78, Village: Sangamner, Owner: Shyam Patil s/o Ganesh Patil")
    print("  Area: 3 Acres 15 Gunthas, Value: Rs. 12,50,000")
    print("  (Plus one additional clause about survey)")

    result = compare_documents_semantic(doc_a, doc_b, debug=True)

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"\nStats: {result['stats']}")
    print("\nIdentical segments:")
    for s in result['identical'][:3]:
        print(f"  - {s[:70]}...")

    print("\nModified segments:")
    for m in result['modified'][:3]:
        print(f"  - Sim: {m['similarity']:.2%}")
        print(f"    Old: {m['original'][:60]}...")
        print(f"    New: {m['updated'][:60]}...")

    print("\nAdded segments:")
    for s in result['added'][:3]:
        print(f"  - {s}")

    return result


def test_identical_documents():
    """Test with nearly identical documents to verify matching works."""
    doc_a = """
    The applicant Shri Ram Kumar has applied for land conversion.
    The application was received on 12/05/2024.
    The concerned officer has verified all documents.
    The application is approved for further processing.
    """

    doc_b = """
    The applicant Shri Ram Kumar has applied for land conversion.
    The application was received on 12/05/2024.
    The concerned officer has verified all documents.
    The application is approved for further processing.
    """

    print("\n" + "=" * 80)
    print("TESTING IDENTICAL DOCUMENTS")
    print("=" * 80)

    result = compare_documents_semantic(doc_a, doc_b, debug=True)

    print(f"\nResults: {result['stats']}")
    print(f"All segments should be IDENTICAL: {len(result['identical'])} identical found")

    return result


if __name__ == "__main__":
    # Run tests
    print("\n" + "#" * 80)
    print("# TEST 1: Zilla Parishad-style documents with variations")
    print("#" * 80)
    test_comparison()

    print("\n" + "#" * 80)
    print("# TEST 2: Identical documents")
    print("#" * 80)
    test_identical_documents()