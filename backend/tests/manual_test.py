"""
Manual end-to-end test script — tests every API endpoint against the live server.
Run:  python tests/manual_test.py   (with the server running on port 8000)
"""

import requests
import json
import sys

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

def report(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  —  {detail}")


print("=" * 60)
print("  MANUAL API ENDPOINT TESTS")
print("=" * 60)

# ── 1. Health check ─────────────────────────────────────────
print("\n[1] GET / — Health check")
r = requests.get(f"{BASE}/")
report("status 200", r.status_code == 200, f"got {r.status_code}")
report("message correct", r.json().get("message") == "PDF Summarizer API is running")

# ── 2. Upload valid PDF ─────────────────────────────────────
print("\n[2] POST /api/upload — Valid PDF")
with open("../dummy_case.pdf", "rb") as f:
    r = requests.post(f"{BASE}/api/upload", files={"file": ("dummy_case.pdf", f, "application/pdf")})
report("status 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
report("has 'text'", "text" in data)
report("has 'page_count'", "page_count" in data)
report("has 'word_count'", "word_count" in data)
report("has 'pages' list", isinstance(data.get("pages"), list))
extracted_text = data.get("text", "")
print(f"      Extracted {data.get('word_count')} words, {data.get('page_count')} pages")

# ── 3. Upload invalid file ──────────────────────────────────
print("\n[3] POST /api/upload — Invalid file type")
r = requests.post(f"{BASE}/api/upload", files={"file": ("test.txt", b"hello", "text/plain")})
report("status 400", r.status_code == 400, f"got {r.status_code}")

# ── 4. Upload wrong extension ───────────────────────────────
print("\n[4] POST /api/upload — Wrong extension")
with open("../dummy_case.pdf", "rb") as f:
    r = requests.post(f"{BASE}/api/upload", files={"file": ("test.docx", f, "application/pdf")})
report("status 400", r.status_code == 400, f"got {r.status_code}")

# ── 5. Summarize (short) ────────────────────────────────────
print("\n[5] POST /api/summarize — Short summary")
if len(extracted_text) >= 50:
    r = requests.post(f"{BASE}/api/summarize", json={"text": extracted_text, "length": "short"})
    report("status 200", r.status_code == 200, f"got {r.status_code}")
    d = r.json()
    report("has 'summary'", "summary" in d)
    report("has 'method'", d.get("method") in ("abstractive", "extractive"))
    report("has 'compression_ratio'", "compression_ratio" in d)
    report("has 'original_stats'", "original_stats" in d)
    print(f"      Method: {d.get('method')}, Words: {d.get('summary_word_count')}, "
          f"Compression: {d.get('compression_ratio')}%")
    print(f"      Summary: {d.get('summary', '')[:150]}...")
else:
    print("  SKIP  extracted text too short")

# ── 6. Summarize (medium) ───────────────────────────────────
print("\n[6] POST /api/summarize — Medium summary")
if len(extracted_text) >= 50:
    r = requests.post(f"{BASE}/api/summarize", json={"text": extracted_text, "length": "medium"})
    report("status 200", r.status_code == 200, f"got {r.status_code}")
    d = r.json()
    report("length_setting is medium", d.get("length_setting") == "medium")
    print(f"      Words: {d.get('summary_word_count')}, Compression: {d.get('compression_ratio')}%")

# ── 7. Summarize (long) ─────────────────────────────────────
print("\n[7] POST /api/summarize — Long summary")
if len(extracted_text) >= 50:
    r = requests.post(f"{BASE}/api/summarize", json={"text": extracted_text, "length": "long"})
    report("status 200", r.status_code == 200, f"got {r.status_code}")
    d = r.json()
    report("length_setting is long", d.get("length_setting") == "long")

# ── 8. Summarize too-short text ──────────────────────────────
print("\n[8] POST /api/summarize — Text too short error")
r = requests.post(f"{BASE}/api/summarize", json={"text": "Hi", "length": "short"})
report("status 400", r.status_code == 400, f"got {r.status_code}")
report("error detail present", "detail" in r.json())

# ── 9. Keywords (NER + frequency) ────────────────────────────
print("\n[9] POST /api/keywords — NER keyword extraction")
r = requests.post(f"{BASE}/api/keywords", json={"text": extracted_text, "top_n": 15})
report("status 200", r.status_code == 200, f"got {r.status_code}")
d = r.json()
kws = d.get("keywords", [])
report("has keywords", len(kws) > 0)
has_type = all("type" in kw for kw in kws)
report("all keywords have 'type'", has_type)

ner_types = set()
for kw in kws:
    ner_types.add(kw.get("type", ""))
    tag = kw.get("type", "?")
    score = kw.get("score", 0)
    word = kw.get("keyword", "")
    print(f"      {tag:12s} | score={score:3} | {word}")

has_ner = len(ner_types - {"FREQUENCY"}) > 0
report("NER entities detected (not just FREQUENCY)", has_ner, f"types: {ner_types}")

# ── 10. Keywords too short ───────────────────────────────────
print("\n[10] POST /api/keywords — Text too short error")
r = requests.post(f"{BASE}/api/keywords", json={"text": "Hi", "top_n": 5})
report("status 400", r.status_code == 400, f"got {r.status_code}")

# ── 11. Download TXT ─────────────────────────────────────────
print("\n[11] POST /api/download — Download as TXT")
r = requests.post(f"{BASE}/api/download", json={
    "summary": "This is a test summary.",
    "original_word_count": 100,
    "summary_word_count": 5,
    "format": "txt"
})
report("status 200", r.status_code == 200, f"got {r.status_code}")
report("content-type text/plain", "text/plain" in r.headers.get("content-type", ""))
report("contains report header", "PDF SUMMARY REPORT" in r.text)

# ── 12. Download PDF ─────────────────────────────────────────
print("\n[12] POST /api/download — Download as PDF")
r = requests.post(f"{BASE}/api/download", json={
    "summary": "This is a test summary.",
    "original_word_count": 100,
    "summary_word_count": 5,
    "format": "pdf"
})
report("status 200", r.status_code == 200, f"got {r.status_code}")
report("content-type application/pdf", "application/pdf" in r.headers.get("content-type", ""))
report("PDF magic bytes", r.content[:5] == b"%PDF-")
print(f"      PDF size: {len(r.content)} bytes")

# ── 13. Download invalid format ──────────────────────────────
print("\n[13] POST /api/download — Invalid format error")
r = requests.post(f"{BASE}/api/download", json={"summary": "Test", "format": "docx"})
report("status 400", r.status_code == 400, f"got {r.status_code}")

# ── SUMMARY ──────────────────────────────────────────────────
print("\n" + "=" * 60)
total = passed + failed
print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    sys.exit(1)
