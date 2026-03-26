# Zilla Parishad — Legal Case PDF Summarizer

A full-stack web application designed to extract text from PDF documents and generate highly-accurate, concise summaries using Natural Language Processing (NLP).

## Features
- **PDF Upload & Text Extraction**: Reliable extraction from PDF files.
- **AI-Powered Summarization**: Utilizes Hugging Face's `facebook/bart-large-cnn` model for abstractive summarization.
- **Customizable Summary Lengths**: Choose between Short, Medium, or Long summaries.
- **Document Intelligence**: Extracts key entities, topics, and reading-time metrics.
- **Download Options**: Save results as PDF or Plain Text.
- **Modern UI**: Built with React, featuring a sleek dark-mode glassmorphism design.

## Tech Stack
- **Frontend**: React.js, Vite, Axios, React Dropzone
- **Backend**: Python, FastAPI, Uvicorn
- **NLP & Processing**: `transformers` (BART), `spacy`, `pdfplumber`

---

## 🏗️ High-Level Architecture

```
  ┌──────────────────┐       HTTP        ┌──────────────────┐
  │  👤 User Browser │  ◄──────────────► │  ⚙️ FastAPI      │
  │  (React Frontend)│                   │  (Python Server) │
  └──────────────────┘                   └────────┬─────────┘
                                                  │
                                                  ▼
                                         ┌──────────────────┐
                                         │  🤖 NLP Engine   │
                                         │  (BART / spaCy)  │
                                         └──────────────────┘
```

The app is split into two independent halves that talk via HTTP:

| Layer | Tech | Port | Purpose |
|-------|------|------|---------|
| **Frontend** | React + Vite | `5173` | The UI the user sees and interacts with |
| **Backend** | FastAPI (Python) | `8000` | Receives PDFs, runs NLP, returns results |

---

## 📂 Project Structure

```
project_NLP/
├── backend/                  ← Python server
│   ├── main.py               ← App entry point (FastAPI setup)
│   ├── requirements.txt      ← Python dependencies
│   ├── routers/
│   │   └── summarize.py      ← All API endpoint definitions
│   ├── services/
│   │   ├── pdf_service.py    ← PDF validation & text extraction
│   │   ├── nlp_service.py    ← Summarization & keyword extraction
│   │   └── download_service.py ← Generate downloadable PDF/TXT files
│   └── tests/                ← Automated test suite
│       ├── conftest.py       ← Shared fixtures (test data)
│       ├── test_api.py       ← API endpoint tests
│       ├── test_pdf_service.py
│       └── test_nlp_service.py
│
├── frontend/                 ← React UI
│   ├── src/
│   │   ├── main.jsx          ← React entry point
│   │   ├── App.jsx           ← Main app (state & logic hub)
│   │   ├── api.js            ← HTTP calls to backend
│   │   ├── index.css         ← Global styles
│   │   ├── App.css           ← Component styles
│   │   └── components/
│   │       ├── Header.jsx         ← App title bar
│   │       ├── FileUpload.jsx     ← Drag-and-drop PDF upload
│   │       ├── SummaryOptions.jsx ← Short/Medium/Detailed selector
│   │       ├── ResultsPanel.jsx   ← Summary + keywords display
│   │       ├── DownloadBar.jsx    ← Export buttons (PDF/TXT)
│   │       └── LoadingSpinner.jsx ← Full-screen loading overlay
│   └── package.json
│
└── README.md
```

---

## 🔄 How Data Flows (Step by Step)

Here's what happens when a user uploads a PDF and gets a summary:

1. **User drops a PDF** → React sends the file to `POST /api/upload`
2. **Backend validates the PDF** → Checks file type, size, magic bytes (`%PDF-`)
3. **Text is extracted** → `pdfplumber` reads every page and extracts text
4. **Frontend receives text + stats** → word count, page count, reading time
5. **Keywords are extracted** → `POST /api/keywords` → spaCy NER + frequency analysis
6. **Text is summarized** → `POST /api/summarize` → BART model generates a summary
7. **User downloads results** → `POST /api/download` → PDF or TXT file is generated and streamed

---

## ⚙️ Backend — Detailed Breakdown

### 1. `main.py` — The Entry Point

**What it does:** Creates the FastAPI server and wires everything together.

| Concept | Simple Explanation |
|---------|-------------------|
| `FastAPI()` | Creates the web server |
| `CORSMiddleware` | Allows the React app (on port 5173) to talk to the backend (on port 8000). Without this, browsers block the requests. |
| `include_router` | Plugs in the `/api/...` endpoints from `summarize.py` |
| `GET /` | A simple health check — hit `http://localhost:8000/` to see if the server is alive |

**How to run it:** `uvicorn main:app --reload --port 8000`

---

### 2. `summarize.py` — The API Endpoints

This file defines **4 endpoints** (think of them as URLs the frontend can call):

| Endpoint | Method | What It Does |
|----------|--------|-------------|
| `/api/upload` | POST | Receives a PDF file → validates it → extracts text → returns text + stats |
| `/api/summarize` | POST | Receives text + length preference → runs AI summarization → returns summary |
| `/api/keywords` | POST | Receives text → extracts named entities & keywords → returns keyword list |
| `/api/download` | POST | Receives summary text + format → generates a PDF or TXT file → returns it for download |

**Key design choices:**
- Each endpoint uses **Pydantic models** (`SummarizeRequest`, `KeywordsRequest`, `DownloadRequest`) to define what data it expects — this gives automatic validation and clear documentation
- Minimum text lengths are enforced (50 chars for summary, 20 for keywords) to prevent garbage results

---

### 3. `pdf_service.py` — PDF Handling

Two functions, each doing one clear job:

#### `validate_pdf(file_bytes, content_type, filename)`
Runs **4 checks** before accepting a PDF:
1. ✅ Content type must be `application/pdf`
2. ✅ Filename must end with `.pdf`
3. ✅ File must be ≤ 20 MB
4. ✅ First 5 bytes must be `%PDF-` (the "magic bytes" that every real PDF starts with)

If any check fails → HTTP error is raised immediately.

#### `extract_text_from_pdf(file_bytes)`
- Uses **pdfplumber** library to open the PDF in memory (no temp files needed)
- Loops through every page, extracting text
- Returns: full text, page count, word count, reading time (at 200 words/minute), and per-page breakdown
- If the PDF has no extractable text (e.g., it's a scanned image) → raises a 422 error

---

### 4. `nlp_service.py` — The AI Brain 🧠

This is the most complex file. It handles **two AI tasks**:

#### A. Text Summarization

**BART Summarization (Primary):**
- Uses Facebook's `bart-large-cnn` model from Hugging Face
- The model is **lazy-loaded** — loaded only on the first request, then kept in memory
- For long documents, text is **chunked** into ~3000-character pieces (because BART can only handle ~1024 tokens at a time)
- Each chunk is summarized separately, then results are combined
- If the combined summary is still too long, it does a **second pass** to condense further
- Supports 3 length settings: `short` (30-80 words), `medium` (80-200 words), `long` (150-400 words)

**Extractive Summarization (Fallback):**
- Used when BART can't load (no internet, not enough RAM, etc.)
- Scores each sentence by counting how many "important" words it contains
- Gives a position boost to early sentences (they tend to be more important)
- Picks the top-ranked sentences and presents them in original order

#### B. Keyword Extraction

- **Primary:** spaCy finds named entities (PERSON, ORG, GPE, LAW, DATE, etc.) — perfect for legal documents
- **Frequency fallback:** Counts word occurrences, filters stop words (the, a, and, etc.), returns most frequent
- **Hybrid approach:** NER entities are ranked first, then frequency-based keywords fill remaining slots

---

### 5. `download_service.py` — File Generation

Two output formats:

| Format | Library | Output |
|--------|---------|--------|
| **PDF** | `fpdf2` | A styled document with title, stats bar, summary body, and footer |
| **TXT** | Built-in Python | A plain text report with ASCII art borders |

Both include: original word count, summary word count, and compression ratio.

---

### 6. `requirements.txt` — Python Dependencies

| Package | What It's For |
|---------|--------------|
| `fastapi` | The web framework |
| `uvicorn` | Server that runs FastAPI |
| `python-multipart` | Handles file uploads |
| `pdfplumber` | Extracts text from PDFs |
| `fpdf2` | Generates PDF download files |
| `transformers` | Hugging Face — provides the BART model |
| `torch` | PyTorch — the engine BART runs on |
| `spacy` | NLP library for keyword/entity extraction |
| `pytest` | Testing framework |
| `httpx` | HTTP client (used by pytest for async tests) |

---

## 🎨 Frontend — Detailed Breakdown

### 1. `App.jsx` — The Brain of the UI

This is the **central hub** that manages all application state and orchestrates the flow:

**State variables:**
| Variable | Type | Purpose |
|----------|------|---------|
| `loadingMsg` | string | Shows/hides the loading spinner with a custom message |
| `errorMsg` | string | Displays error alerts |
| `originalText` | string | The full text extracted from the uploaded PDF |
| `summaryResult` | object | The AI-generated summary + metadata |
| `keywords` | array | List of extracted keywords with types |
| `selectedLength` | string | Current summary length preference (short/medium/long) |

**Key functions:**
- `handleFileUpload(file)` → Uploads PDF → extracts text → extracts keywords → summarizes (all in sequence)
- `handleSummarize(text, length)` → Calls the summarize API
- `onLengthChange(length)` → When user picks a different length, automatically re-summarizes
- `handleDownload(format)` → Triggers file download (PDF or TXT)

---

### 2. `api.js` — API Communication Layer

A thin wrapper around `axios` that maps to backend endpoints:

| Function | Calls | Sends | Returns |
|----------|-------|-------|---------|
| `uploadPdf(file)` | `POST /api/upload` | Form data with PDF | Extracted text + stats |
| `summarizeText(text, length)` | `POST /api/summarize` | Text + length preference | Summary + metadata |
| `extractKeywords(text)` | `POST /api/keywords` | Text | Keywords array |
| `downloadSummary(...)` | `POST /api/download` | Summary + format | Triggers browser download |

The `downloadSummary` function does something clever: it creates a temporary `<a>` link, clicks it programmatically to trigger the browser's native download dialog, then cleans up.

---

### 3. React Components

#### `Header.jsx`
- Displays the app title "**Zilla Parishad**" with a briefcase icon
- Subtitle: "Legal Case Summarizer"
- Uses gradient text effect on "Parishad"

#### `FileUpload.jsx`
- **Drag-and-drop zone** using the `react-dropzone` library
- Accepts only `.pdf` files, max 20 MB
- Shows the file name and size after selection
- Handles errors: wrong file type, file too large

#### `SummaryOptions.jsx`
- Three clickable cards: **Short** / **Medium** / **Detailed**
- Each shows an icon and word count range
- Selecting a different length automatically re-runs summarization

#### `ResultsPanel.jsx`
- **Tabbed view** — switch between "Case Summary" and "Original Case Text"
- Right sidebar shows **statistics** (word counts, compression ratio) and **Legal Entities & Key Terms** as colored chips
- Uses a glass-panel design with fade-in animation

#### `DownloadBar.jsx`
- Two buttons: "Download TXT" and "Download Case Summary (PDF)"
- Disabled while loading or downloading

#### `LoadingSpinner.jsx`
- Full-screen overlay with a spinning animation
- Shows a custom message (e.g., "Extracting text from Case File...")

---

## 🧪 Test Suite

The project includes a comprehensive **pytest** test suite with 3 test files:

### `conftest.py` — Shared Test Fixtures
- `client` → a FastAPI TestClient (simulates HTTP requests without running a real server)
- `sample_text` → a realistic legal text about a Supreme Court judgment
- `sample_pdf_bytes` → a real PDF generated in memory using fpdf2
- `short_text` → text that's too short (for testing error handling)

### `test_api.py` — API Integration Tests

| Test Class | Tests |
|-----------|-------|
| `TestUploadEndpoint` | Valid PDF upload, invalid file type, wrong extension |
| `TestSummarizeEndpoint` | Valid text, too-short text, default length |
| `TestKeywordsEndpoint` | Valid text, too-short text |
| `TestDownloadEndpoint` | TXT download, PDF download, invalid format |
| `TestHealthCheck` | Root endpoint returns correct message |

### `test_pdf_service.py` & `test_nlp_service.py`
- Unit tests for individual service functions
- Test PDF validation rules, text extraction, summarization, and keyword extraction

**Run all tests:**
```bash
cd backend
python -m pytest tests/ -v
```

---

## 🚀 Setup Instructions

### Prerequisites
- Node.js (v16+ recommended)
- Python (v3.9+ recommended)

### 1. Backend Setup (FastAPI)

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --reload --port 8000
```

The API docs are available at `http://localhost:8000/docs`

> **Note:** On the first summarization request, the Hugging Face BART model (~1.6 GB) will be downloaded automatically.

### 2. Frontend Setup (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 3. Run the Tests

```bash
cd backend
python -m pytest tests/ -v
```

---

## 💡 Key Design Decisions

| Decision | Why |
|----------|-----|
| **Lazy-loading AI models** | BART is ~1.6 GB. Loading it at startup would slow down the server. Instead, it loads on the first summarize request. |
| **Dual fallback system** | If BART can't load (no GPU, offline), the app still works with extractive summarization. Same for spaCy → frequency fallback. |
| **Chunked summarization** | BART has a 1024-token limit. We split long documents into ~3000-char chunks, summarize each, then optionally do a second pass. |
| **Pydantic request models** | Automatic input validation + auto-generated API docs at `/docs`. |
| **pdfplumber over PyPDF2** | More reliable text extraction, especially for complex layouts. |
| **Hybrid keyword extraction** | spaCy NER catches legal entities (people, courts, laws); frequency analysis catches domain-specific terms that aren't named entities. |
| **In-memory PDF generation** | No temp files on disk — the download PDF is generated in memory and streamed directly. |

---

## 💡 Future Enhancements (Roadmap)
- **User Authentication**: Allow users to save their summaries history securely.
- **Multi-language Support**: Implement translation pipelines using multilingual models (like mBART).
- **Batch Processing**: Allow summarizing multiple PDFs simultaneously.
- **Database Integration**: Store analytics on document lengths, average processing time, and keyword trends.
