import sys
import os
import json
import io

# Force stdout to use utf-8 to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.difference_engine import compare_documents_semantic

def verify_zilla_parishad_comparison():
    print("#" * 80)
    print("# VERIFYING ZILLA PARISHAD DOCUMENT COMPARISON")
    print("#" * 80)

    # Mock Data based on User Request
    doc_a = (
        "Plot 123 owned by Ram. "
        "The application for land conversion was submitted by Shri Ram Kumar s/o Hari Kumar on 12/05/2024. "
        "The survey conducted at Village Rahuri, Taluka Rahuri shows no encumbrances. "
        "As per Seven Twelve Extract, the property is clear."
    )

    doc_b = (
        "Plot 456 owned by Shyam. "
        "The application for land conversion was submitted by Shri Shyam Patil s/o Ganesh Patil on 25/07/2024. "
        "The survey conducted at Village Sangamner, Taluka Sangamner shows no encumbrances. "
        "As per Seven Twelve Extract, the property is clear."
    )

    print("\n[STEP 1] Running semantic comparison...")
    result = compare_documents_semantic(doc_a, doc_b, debug=True)

    print("\n[STEP 2] Verifying Output Format...")
    expected_keys = ["identical", "modified", "added", "removed", "similarities", "differences", "shared_topics", "shared_blocks"]
    missing_keys = [k for k in expected_keys if k not in result]
    
    if not missing_keys:
        print("  ✅ All required UI keys found: Similarities, Differences, Topics, Blocks")
    else:
        print(f"  ❌ Missing keys: {missing_keys}")

    print("\n[STEP 3] Checking Similarity Detection & Enrichment...")
    
    # Check if we have entries in similarities/differences
    has_sim_cats = len(result.get("similarities", [])) > 0
    has_diff_cats = len(result.get("differences", [])) > 0
    has_shared_blocks = len(result.get("shared_blocks", [])) > 0
    
    print(f"  Enrichment: {len(result.get('similarities', []))} similarity categories")
    print(f"  Enrichment: {len(result.get('differences', []))} difference categories")
    print(f"  Enrichment: {len(result.get('shared_blocks', []))} identical blocks")
    
    if has_sim_cats and has_shared_blocks:
        print("  ✅ SUCCESS: Enriched data present for UI rendering")
    else:
        print("  ❌ FAILURE: Missing enriched data sections")

    print("\n[STEP 4] Checking Entity Extraction Noise...")
    entities_a = result["debug_info"].get("entities_a", {}) if "entities_a" in result.get("debug_info", {}) else {}
    
    # Names can be in similarities OR differences
    sim_names = [item for cat in result.get("similarities", []) if cat["category"] == "Persons / Parties" for item in cat["items"]]
    diff_names_1 = [item for cat in result.get("differences", []) if cat["category"] == "Persons / Parties" for item in cat["only_in_doc1"]]
    diff_names_2 = [item for cat in result.get("differences", []) if cat["category"] == "Persons / Parties" for item in cat["only_in_doc2"]]
    
    all_names = list(set(sim_names + diff_names_1 + diff_names_2))
    
    print(f"  Extracted Names (Combined): {all_names}")
    
    # Check for suspected noise
    noise_found = [n for n in all_names if n.lower() in ["shri", "smt", "the", "kumar", "smtrimati", "for", "submitted"]]
    if noise_found:
        print(f"  ❌ Noise detected in names: {noise_found}")
    else:
        print("  ✅ No common noise detected in names.")
    
    # Verify real names are caught
    real_names = [n for n in all_names if "Ram Kumar" in n or "Shyam Patil" in n]
    if real_names:
        print(f"  ✅ SUCCESS: Real names captured: {real_names}")
    else:
        print("  ❌ FAILURE: Real names were filtered out!")

    print("\n[STEP 5] Sample Output (JSON format):")
    # Only show a subset for brevity
    sample_json = {
        "identical": result["identical"][:1],
        "modified": [{
            "original": m["original"][:50] + "...",
            "updated": m["updated"][:50] + "...",
            "similarity": m["similarity"]
        } for m in result["modified"][:2]],
        "added": result["added"][:1],
        "removed": result["removed"][:1]
    }
    print(json.dumps(sample_json, indent=2))

if __name__ == "__main__":
    verify_zilla_parishad_comparison()
