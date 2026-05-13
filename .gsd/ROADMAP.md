# Roadmap: Milestone 2 (Enterprise Capabilities)

**Objective**: Enhance the app with Global RAG Chat, Admin Dashboard (RBAC), and V2 Multi-language Support.

---

## Phase 1: Multi-language Support V2 (Backend & Frontend)
**Goal:** Wire the UI language dropdown to the backend translation pipeline so users can read and download summaries in multiple languages.
- [x] Ensure `nlp_service.py` correctly translates generated summaries based on the `language` query parameter.
- [x] Update frontend `SummaryOptions.jsx` to pass the selected language to the API.
- [x] Ensure `DownloadBar.jsx` downloads the correct localized string.
- [x] **Verification**: Generate a summary in Marathi and download the PDF to confirm encoding and translation.

## Phase 2: Admin Dashboard & RBAC
**Goal:** Introduce user roles and create an administrative dashboard.
- [x] Add `is_admin` boolean to `models.User` in `models.py`.
- [x] Create Alembic migration or DB script to update existing `app.db` schema.
- [x] Create an `AdminRoute` wrapper in the frontend and a new `AdminDashboard.jsx`.
- [x] Implement backend endpoints (e.g., `/admin/stats`) restricted by a dependency checking the JWT for admin privileges.
- [x] **Verification**: Attempt to access `/admin/stats` as a normal user (expect 403), then as an admin (expect 200).

## Phase 3: Global Multi-modal Chat (Cross-case RAG)
**Goal:** Enhance the ChatBot to RAG across the entire 290-case FAISS database.
- [x] Update `vector_service.py` to allow querying without filtering by a specific `case_id`.
- [x] Update the `ChatBot.jsx` UI to include a toggle for "Document Mode" vs "Global Mode".
- [x] Update `routers/chat.py` to accept the `global_mode` flag and route the FAISS RAG query accordingly.
- [x] **Verification**: Ask a global query (e.g., "Summarize agricultural trends") and verify the LLM utilizes chunks from multiple different case documents.
