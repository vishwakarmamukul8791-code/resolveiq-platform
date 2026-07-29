# ResolveIQ — Enterprise AI Incident Intelligence Platform

**ResolveIQ** is a full-stack Retrieval-Augmented Generation (RAG) platform that helps IT support engineers resolve incidents by retrieving relevant information from historical tickets and knowledge base documents, then generating grounded, source-cited answers — with explicit confidence signaling instead of hallucination.

Built as a production-style reference implementation: role-based authentication, a hybrid retrieval pipeline (BM25 + semantic search + reciprocal rank fusion + cross-encoder reranking), an admin analytics suite, and a React frontend — not a notebook demo.

---

## Problem Statement

Support engineers spend significant time searching historical incidents and KB documents for solutions. Keyword search misses semantically relevant results, and naive LLM wrappers hallucinate when they don't actually know the answer.

ResolveIQ addresses both: a hybrid retrieval pipeline finds relevant context using both lexical (BM25) and semantic (embedding) search, a cross-encoder reranks the combined candidates for precision, and a confidence-scoring layer tells the engineer — explicitly — whether an answer is well-grounded, partially grounded, or not found at all, rather than presenting every answer with false confidence.

---

## Key Features

### Authentication & Access Control
- JWT-based auth, PBKDF2 password hashing
- Two roles: **Admin** and **Support Engineer**
- Forced password reset on first login for newly created accounts
- Per-session tracking (login/logout, duration, question count)

### Document Management
- Upload PDF, TXT, and CSV documents
- SHA-256 duplicate detection (skips reprocessing identical content)
- Document registry, list, delete
- Chunk-level retrieval with page/location metadata for source attribution

### Retrieval Pipeline
- **Hybrid search**: BM25 (lexical) + FAISS semantic search, combined via Reciprocal Rank Fusion (RRF)
- **Cross-encoder reranking** (`cross-encoder/ms-marco-MiniLM-L-6-v2`) over the fused candidate set for final precision
- **Query rewriting** before retrieval to improve match quality on conversational phrasing
- Configurable chunk size, overlap, and Top-K
- Optional document-scoped search

### Confidence-Aware Generation
- Every answer is scored **High / Medium / Low** based on retrieval relevance, not just returned unconditionally
- Low-confidence questions return an explicit "not found" response rather than a hallucinated guess
- Gemini 2.5 Flash generates the final answer, grounded strictly in retrieved context

### History & Session Tracking
- Full question/answer history per engineer, with pin/unpin and delete
- Session-level login/logout duration tracking

### Admin Analytics
- Engineer account management (create, enable/disable, reset password)
- Adoption analytics: question volume, confidence distribution, per-engineer activity
- **Knowledge gap detection**: recurring low-confidence questions, surfaced as candidates for new documentation
- Source analytics: most-cited documents across all answers
- System health and corpus statistics dashboard

### Frontend
- React 19 + Vite single-page application
- Full auth flow, Support workspace (ChatGPT-style conversation UI), 5-tab Admin dashboard
- Light/dark theming, source-document viewer, real-time document upload/processing

---

## Architecture

### Document Processing Flow
1. Upload document (PDF/TXT/CSV)
2. Compute SHA-256 hash; skip if already indexed
3. Extract and clean text
4. Split into overlapping chunks
5. Generate embeddings (`all-MiniLM-L6-v2`)
6. Store vectors in FAISS; store chunk metadata (document, page, location) alongside
7. Update the document registry

### Question Answering Flow
1. Engineer submits a question (optionally scoped to one document)
2. Query is rewritten for better retrieval matching
3. Rewritten query is embedded and searched against FAISS (semantic) **and** BM25 (lexical) in parallel
4. Results are combined via Reciprocal Rank Fusion
5. Fused candidates are reranked by a cross-encoder
6. Top-K reranked chunks are scored for confidence (High/Medium/Low)
7. If confidence is sufficient, the context is passed to Gemini 2.5 Flash to generate a grounded answer; if not, a "not found" response is returned without calling the LLM
8. Response includes the answer, confidence level, source documents (with page/location), and the retrieval score — saved to history

---

## Technology Stack

| Category | Technology |
|---|---|
| Backend | FastAPI, Python |
| Frontend | React 19, Vite, React Router v7 |
| AI Model | Google Gemini 2.5 Flash |
| Embedding Model | `all-MiniLM-L6-v2` (384-dim) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Lexical Search | BM25 (`rank-bm25`) |
| Vector Database | FAISS |
| Auth | PyJWT, PBKDF2 password hashing |
| Data Storage | JSON (no external database) |
| Libraries | Sentence Transformers, Transformers, PyTorch, NumPy, Pandas, Pydantic, pypdf, pdfplumber |
| Frontend Libraries | `xlsx` (Excel export) |

---

## Project Structure
.
├── .env.example
├── .gitignore
├── app.py
├── README.md
├── requirements.txt
│
├── backend
│ ├── routes
│ │ ├── admin.py
│ │ ├── ask.py
│ │ ├── auth.py
│ │ ├── debug_retrieval.py
│ │ ├── delete_document.py
│ │ ├── delete_history.py
│ │ ├── document_details.py
│ │ ├── documents.py
│ │ ├── health.py
│ │ ├── history.py
│ │ ├── process.py
│ │ ├── search.py
│ │ ├── stats.py
│ │ └── upload.py
│ │
│ ├── services
│ │ ├── auth_service.py
│ │ ├── bm25_service.py
│ │ ├── cleaning_service.py
│ │ ├── confidence_service.py
│ │ ├── document_registry.py
│ │ ├── embedding_service.py
│ │ ├── extraction_service.py
│ │ ├── faiss_service.py
│ │ ├── hash_service.py
│ │ ├── health_service.py
│ │ ├── history_service.py
│ │ ├── hybrid_retrieval_service.py
│ │ ├── llm_service.py
│ │ ├── logging_service.py
│ │ ├── query_rewrite_service.py
│ │ ├── reindex_service.py
│ │ ├── rerank_service.py
│ │ ├── retrieval_contract.py
│ │ ├── retrieval_service.py
│ │ ├── session_service.py
│ │ ├── stats_service.py
│ │ └── vector_store.py
│ │
│ ├── seed_admin.py
│ ├── config.py
│ └── logger.py
│
├── data (git-ignored, generated at runtime)
│ ├── users.json
│ ├── sessions.json
│ ├── document_registry.json
│ ├── history/chat_history.json
│ ├── raw/
│ └── vector_store/
│ ├── index.faiss
│ └── metadata.json
│
└── frontend
├── index.html
├── package.json
├── vite.config.js
├── public/
│ └── favicon.png
└── src
├── main.jsx
├── App.jsx
├── index.css
├── api/client.js
├── assets/resolveiq-mark.png
├── context/
│ ├── AuthContext.jsx
│ └── ThemeContext.jsx
├── utils/formatTime.js
├── pages/
│ ├── Landing.jsx
│ ├── SupportDashboard.jsx
│ ├── AdminDashboard.jsx
│ └── NotFound.jsx
├── components/
│ ├── Navbar.jsx, Hero.jsx, CapabilityGrid.jsx, CapabilityCard.jsx
│ ├── LoginPanel.jsx, PlatformStatus.jsx, ThemeToggle.jsx
│ ├── ProtectedRoute.jsx, AccountMenu.jsx
│ ├── IncidentWorkspace.jsx, SupportSidebar.jsx
│ ├── SourceViewerModal.jsx, HelpModal.jsx
│ └── admin/
│ ├── AdminOverviewTab.jsx, AdminEngineersTab.jsx
│ ├── AdminDocumentsTab.jsx, AdminRagInsightsTab.jsx
│ ├── AdminHealthTab.jsx
│ └── CreateEngineerModal.jsx, TempPasswordModal.jsx
└── styles/
└── (one stylesheet per component/page, plus theme.css —
the single source of truth for all design tokens)


---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Log in, returns JWT + session ID |
| POST | `/auth/logout` | End the current session |
| POST | `/auth/reset-password` | Set a new password (self-service, e.g. forced first-login reset) |
| GET | `/auth/me` | Get the current user's identity from their token |

### Core RAG
| Method | Endpoint | Description |
|---|---|---|
| GET | `/ask` | Ask a question; returns answer, confidence, sources |
| GET | `/debug/retrieval` | Inspect raw retrieval internals for a query |

### Documents
| Method | Endpoint | Description |
|---|---|---|
| POST | `/upload` | Upload a raw document |
| POST | `/process-document` | Chunk, embed, and index an uploaded document |
| GET | `/documents` | List all indexed documents |
| GET | `/document/{filename}` | Get a document's full chunk-level content |
| DELETE | `/document/{filename}` | Remove a document and reindex |

### History
| Method | Endpoint | Description |
|---|---|---|
| GET | `/history` | Get the current user's Q&A history |
| PATCH | `/history/{entry_id}/pin` | Toggle pin on a history entry |
| DELETE | `/history` | Clear all history for the current user |
| DELETE | `/history/{entry_id}` | Delete a single history entry |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| POST | `/admin/create-engineer` | Create a new engineer account |
| GET | `/admin/engineers` | List all engineer accounts with usage stats |
| POST | `/admin/set-active` | Enable/disable an engineer account |
| POST | `/admin/reset-engineer-password` | Admin-initiated password reset |
| GET | `/admin/sessions` | Session-level login/logout logs |
| GET | `/admin/analytics` | Adoption KPIs and confidence distribution |
| GET | `/admin/knowledge-gaps` | Recurring low-confidence questions |
| GET | `/admin/source-analytics` | Most-cited documents |
| GET | `/admin/system-health` | Component health checks + corpus stats |
| GET | `/admin/history/{username}` | View a specific engineer's history |

### System & Evaluation
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Public health check |
| GET | `/stats` | Public corpus/config statistics |
| GET | `/search` | Raw semantic search (evaluation baseline) |
| GET | `/search-bm25` | Raw BM25 search (evaluation baseline) |
| GET | `/search-hybrid` | Hybrid RRF search, pre-rerank (evaluation baseline) |
| GET | `/search-reranked` | Full pipeline output (evaluation baseline) |

---

## Configuration

Retrieval and model settings are centralized in `backend/config.py`:

| Setting | Value |
|---|---|
| Embedding model | `all-MiniLM-L6-v2` |
| Embedding dimension | 384 |
| Vector database | FAISS |
| Chunk size | 500 |
| Chunk overlap | 100 |
| Top-K retrieval | 5 |

---

## Installation & Setup

### Backend
```bash
git clone <repository-url>
cd resolveiq

pip install -r requirements.txt

# create .env with the two required variables — see below
uvicorn app:app --reload
```
Backend runs at `http://127.0.0.1:8000`.

**First-time setup only** — create the initial admin account (interactive):
```bash
python -m backend.seed_admin
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`. To point it at a backend on a different host/port, create `frontend/.env` with:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## Environment Variables

Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_jwt_signing_secret
```
Both are required — the app will not start without `JWT_SECRET_KEY`.

---

## Roadmap

- Docker containerization
- Cloud deployment (persistent storage required — see Architecture notes)
- CI/CD pipeline
- Automated unit and integration tests
- Streaming responses
- Database migration from flat-file JSON storage

---

## License

This project is developed for educational and portfolio purposes.
