# Milestone 2: Enterprise Capabilities

**Status:** FINALIZED

## Objective
Enhance the PDF Summarizer application with enterprise-level features including full cross-case multi-modal RAG chat, an administrative dashboard with Role-Based Access Control (RBAC), and V2 Multi-language support seamlessly integrated into the UI.

## Requirements

### 1. Full Multi-modal Chat (Global RAG)
*   **Current State:** The ChatBot only queries the active/currently opened document. RAG is active but siloed.
*   **Requirement:** Enhance the ChatBot to allow querying across *all* ingested cases in the FAISS vector database.
*   **Acceptance Criteria:**
    *   A user can ask "What are the common trends in agricultural cases?" and RAG retrieves relevant chunks across the entire 290-case dataset.
    *   The UI indicates whether the chat is "Document-specific" or "Global".

### 2. Admin Dashboard & RBAC
*   **Current State:** Basic User model exists with authentication, but all users have the same privileges.
*   **Requirement:** Implement Role-Based Access Control (Admin vs. Standard User) and an Admin Dashboard.
*   **Acceptance Criteria:**
    *   `models.User` updated to include an `is_admin` boolean or `role` string.
    *   Admin Dashboard UI showing system-wide logs (total cases ingested, user counts, API errors).
    *   Protected API endpoints that only allow Admin access.

### 3. Multi-language Support (V2)
*   **Current State:** Deep-translator is in backend requirements and basic logic exists, but UI integration is incomplete.
*   **Requirement:** Seamlessly wire the frontend language dropdown to the backend translation pipeline so users can generate summaries and download them in their native language (e.g., Hindi, Marathi).
*   **Acceptance Criteria:**
    *   UI Language Dropdown explicitly triggers translation on the backend.
    *   Summaries are returned and displayed in the target language.
    *   PDF/TXT downloads retain the selected translated language.

## Exclusions
*   Moving away from SQLite/FAISS to a cloud vector database (e.g., pgvector, Pinecone) is deferred to Milestone 3.
