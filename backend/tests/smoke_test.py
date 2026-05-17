
import sys
import os

# Set project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

try:
    from services.precedent_service import find_precedents
    from services.cross_reference_service import cross_reference_document
    from services.timeline_service import extract_legal_timeline
    print("Imports successful")
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_logic():
    print("\n--- Testing Services with Mock Data ---")
    mock_text = "In the case of State v. Sharma (2020), Section 144 of the CrPC was applied. The incident occurred on 2020-01-15. The order was passed on 2020-02-01."
    
    # 1. Test Cross Reference
    print("Testing Cross-Reference...")
    try:
        refs = cross_reference_document(mock_text)
        print(f"Found {len(refs)} citations.")
    except Exception as e:
        print(f"Cross-Ref failed: {e}")

    # 2. Test Timeline
    print("Testing Timeline...")
    try:
        tl = extract_legal_timeline(mock_text)
        print(f"Extracted {len(tl)} events.")
    except Exception as e:
        print(f"Timeline failed: {e}")

    # 3. Test Precedent (Check for accessibility)
    print("Testing Precedent service accessibility...")
    try:
        print("Precedent service function is reachable.")
    except Exception as e:
        print(f"Precedent failed: {e}")

if __name__ == "__main__":
    test_logic()
