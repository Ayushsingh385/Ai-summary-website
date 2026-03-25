# PDF Summarizer Web Application

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

## 🚀 Setup Instructions

### Prerequisites
- Node.js (v16+ recommended)
- Python (v3.9+ recommended)

### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. (Optional but recommended) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   *Note: On the first request, the Hugging Face BART model (~1.6 GB) will be downloaded automatically.*

### 2. Frontend Setup (React + Vite)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to the local URL provided (usually `http://localhost:5173`).

---

## 📡 API Documentation (Backend)

The backend provides several RESTful endpoints, documented automatically via Swagger. Once the backend is running, visit `http://localhost:8000/docs`.

### Core Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/api/upload` | Upload PDF file (multipart/form-data), returns extracted text and stats. |
| `POST` | `/api/summarize` | Generate abstractive summary from text payload (`text`, `length`). |
| `POST` | `/api/keywords` | Extract keywords from given text using SpaCy or frequency analysis. |
| `POST` | `/api/download` | Generate downloadable PDF or TXT from generated summary payload. |

---

## 💡 Future Enhancements (Roadmap)
- **User Authentication**: Allow users to save their summaries history securely.
- **Multi-language Support**: Implement translation pipelines using multilingual models (like mBART).
- **Batch Processing**: Allow summarizing multiple PDFs simultaneously.
- **Database Integration**: Store analytics on document lengths, average processing time, and keyword trends.
