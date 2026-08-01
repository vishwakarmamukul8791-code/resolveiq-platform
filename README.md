# ResolveIQ — AI-Powered Incident Resolution Platform

ResolveIQ is a full-stack Retrieval-Augmented Generation (RAG) application built to help IT support engineers investigate incidents using internal knowledge-base documents and historical incident records.

The system combines BM25 keyword search with FAISS-based semantic retrieval. Results from both retrievers are merged using Reciprocal Rank Fusion (RRF), reranked with a cross-encoder, and then passed to Gemini only when the retrieved evidence is strong enough.

Support engineers can ask questions, continue investigation threads, review cited sources, and reopen previous conversations. Administrators can manage engineer accounts, upload and process documents, review analytics, and monitor system health.

## Problem

Support engineers often search across multiple knowledge-base documents and incident records before finding a useful solution.

Keyword-only search can miss semantically similar content, while a basic LLM wrapper can generate unsupported answers when relevant evidence is not available.

ResolveIQ addresses both problems by using:

- lexical retrieval with BM25
- semantic retrieval with FAISS and sentence embeddings
- Reciprocal Rank Fusion to merge retrieval results
- cross-encoder reranking for better final ordering
- confidence-based answer generation
- source citations for retrieved evidence

## Main Features

### Authentication and access control

- JWT-based authentication
- PBKDF2-HMAC-SHA256 password hashing
- Admin and Support Engineer roles
- forced password reset for newly created accounts
- account activation and deactivation
- session tracking for login, logout, duration, and question count

### Document management

- PDF, TXT, and CSV upload
- SHA-256 duplicate detection
- text extraction and cleaning
- overlapping chunk generation
- embedding generation and FAISS indexing
- document registry and document details
- safe document deletion with vector-store rebuild
- rollback handling when processing or deletion fails

### Retrieval pipeline

- BM25 lexical retrieval
- FAISS semantic retrieval
- Reciprocal Rank Fusion
- cross-encoder reranking
- query rewriting before retrieval
- optional document-scoped search
- configurable chunk size, overlap, and Top-K

### Answer generation

- Gemini-based answer generation
- High, Medium, and Low confidence levels
- low-confidence abstention instead of unsupported answers
- source document and location metadata
- conversation-aware follow-up questions
- provider timeout and fallback handling

### History and analytics

- conversation history grouped by investigation thread
- reopen previous conversations
- pin and delete investigation threads
- engineer activity analytics
- confidence distribution
- knowledge-gap detection
- source usage analytics
- system health and corpus statistics

## RAG Flow

```text
User question
    |
    v
Query rewriting
    |
    +--------------------+
    |                    |
    v                    v
BM25 retrieval      FAISS retrieval
    |                    |
    +---------+----------+
              |
              v
Reciprocal Rank Fusion
              |
              v
Cross-encoder reranking
              |
              v
Confidence scoring
              |
       +------+------+
       |             |
       v             v
Enough evidence   Low confidence
       |             |
       v             v
Gemini answer     Abstain safely
       |
       v
Answer + citations + history
```

## Document Processing Flow

```text
Upload document
    |
    v
Validate filename and file type
    |
    v
Calculate SHA-256 hash
    |
    v
Extract and clean text
    |
    v
Create overlapping chunks
    |
    v
Generate embeddings
    |
    v
Update FAISS index and metadata
    |
    v
Update document registry
```

## Technology Stack

| Area | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React 19, Vite, React Router 8 |
| Answer model | Gemini 3.6 Flash |
| Query rewriting model | Gemini 3.5 Flash Lite |
| Embedding model | `all-MiniLM-L6-v2` |
| Embedding dimension | 384 |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Lexical retrieval | BM25 with `rank-bm25` |
| Vector index | FAISS |
| PDF extraction | `pdfplumber` |
| Authentication | JWT with HS256 |
| Password hashing | PBKDF2-HMAC-SHA256, 200,000 iterations |
| Runtime storage | JSON files and FAISS |
| Frontend API client | Native `fetch` |

## Retrieval Configuration

The main retrieval settings are stored in `backend/config.py`.

| Setting | Value |
|---|---|
| Embedding model | `all-MiniLM-L6-v2` |
| Embedding dimension | 384 |
| Vector index | FAISS |
| Chunk size | 500 |
| Chunk overlap | 100 |
| Top-K | 5 |

## Offline Retrieval Evaluation

The repository includes an offline evaluation runner:

```bash
python -m backend.eval.run_eval
```

Current retrieval results:

| Method | Hit@1 | Hit@5 | MRR@5 |
|---|---:|---:|---:|
| Semantic | 0.905 | 1.000 | 0.940 |
| BM25 | 0.857 | 1.000 | 0.909 |
| Hybrid using RRF | 0.905 | 1.000 | 0.944 |
| Hybrid with reranking | 0.905 | 1.000 | 0.940 |

The evaluation is used as an offline benchmark. These metrics are not calculated for every question submitted through the frontend.

## Project Structure

```text
resolveiq/
|-- app.py
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
|
|-- backend/
|   |-- config.py
|   |-- logger.py
|   |-- seed_admin.py
|   |
|   |-- eval/
|   |   |-- eval_set.py
|   |   `-- run_eval.py
|   |
|   |-- routes/
|   |   |-- auth.py
|   |   |-- admin.py
|   |   |-- ask.py
|   |   |-- upload.py
|   |   |-- process.py
|   |   |-- documents.py
|   |   |-- document_details.py
|   |   |-- delete_document.py
|   |   |-- history.py
|   |   |-- delete_history.py
|   |   |-- search.py
|   |   |-- stats.py
|   |   |-- health.py
|   |   `-- debug_retrieval.py
|   |
|   `-- services/
|       |-- auth_service.py
|       |-- embedding_service.py
|       |-- bm25_service.py
|       |-- hybrid_retrieval_service.py
|       |-- rerank_service.py
|       |-- query_rewrite_service.py
|       |-- confidence_service.py
|       |-- llm_service.py
|       |-- faiss_service.py
|       |-- vector_store.py
|       |-- document_registry.py
|       |-- history_service.py
|       |-- session_service.py
|       `-- reindex_service.py
|
|-- data/                       # Generated locally and ignored by Git
|   |-- raw/
|   |-- vector_store/
|   |-- history/
|   |-- users.json
|   |-- sessions.json
|   `-- document_registry.json
|
`-- frontend/
    |-- package.json
    |-- package-lock.json
    |-- vite.config.js
    |-- index.html
    |-- public/
    `-- src/
        |-- api/
        |-- assets/
        |-- components/
        |-- context/
        |-- pages/
        |-- styles/
        |-- utils/
        |-- App.jsx
        `-- main.jsx
```

## Local Setup

### Prerequisites

- Python 3.12
- Node.js and npm
- Gemini API key

### 1. Clone the repository

```bash
git clone <repository-url>
cd resolveiq
```

### 2. Create the Python environment

Windows PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS or Linux:

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure backend environment variables

Copy `.env.example` to `.env`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Set the required values:

```env
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_jwt_signing_secret
FRONTEND_ORIGIN=
ENABLE_DEBUG_ROUTES=false
```

Generate a secure JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4. Create the first admin account

```bash
python -m backend.seed_admin
```

The command creates `data/users.json` and prints a temporary password. The admin must change this password after the first login.

### 5. Start the backend

```bash
uvicorn app:app --reload
```

Backend URLs:

```text
API:     http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
Health:  http://127.0.0.1:8000/health
```

### 6. Configure and start the frontend

```bash
cd frontend
npm install
```

Copy the frontend environment template:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Default frontend environment:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Main API Endpoints

### Authentication

| Method | Endpoint | Access |
|---|---|---|
| POST | `/auth/login` | Public |
| POST | `/auth/logout` | Authenticated |
| POST | `/auth/reset-password` | Authenticated |
| GET | `/auth/me` | Authenticated |

### RAG

| Method | Endpoint | Access |
|---|---|---|
| POST | `/ask` | Authenticated |
| GET | `/debug/retrieval` | Admin, only when enabled |

### Documents

| Method | Endpoint | Access |
|---|---|---|
| POST | `/upload` | Admin |
| POST | `/process-document` | Admin |
| GET | `/documents` | Authenticated |
| GET | `/document/{filename}` | Authenticated |
| DELETE | `/document/{filename}` | Admin |

### History

| Method | Endpoint | Access |
|---|---|---|
| GET | `/history` | Authenticated |
| GET | `/history/{conversation_id}` | Authenticated |
| PATCH | `/history/{entry_id}/pin` | Authenticated |
| DELETE | `/history` | Authenticated |
| DELETE | `/history/{entry_id}` | Authenticated |

### Admin

| Method | Endpoint |
|---|---|
| POST | `/admin/create-engineer` |
| GET | `/admin/engineers` |
| POST | `/admin/set-active` |
| POST | `/admin/reset-engineer-password` |
| GET | `/admin/sessions` |
| GET | `/admin/analytics` |
| GET | `/admin/knowledge-gaps` |
| GET | `/admin/source-analytics` |
| GET | `/admin/system-health` |
| GET | `/admin/history/{username}` |

### System and retrieval diagnostics

| Method | Endpoint | Access |
|---|---|---|
| GET | `/health` | Public |
| GET | `/stats` | Public |
| GET | `/search` | Admin |
| GET | `/search-bm25` | Admin |
| GET | `/search-hybrid` | Admin |
| GET | `/search-reranked` | Admin |

## Runtime Data

The application currently uses local JSON files and FAISS instead of an external database.

```text
data/raw/                         Uploaded documents
data/users.json                   User accounts
data/sessions.json                Login sessions
data/document_registry.json       Processed document registry
data/history/chat_history.json    Investigation history
data/vector_store/index.faiss     Vector index
data/vector_store/metadata.json   Chunk metadata
```

These files are ignored by Git because they contain runtime data, user information, or generated indexes.

A file inside `data/raw/` is not searchable until it has been processed and added to the registry, metadata, and FAISS index.

## Security and Reliability

The project includes:

- role checks on admin-only routes
- JWT expiry handling
- password hashing with per-user salt
- filename validation and path traversal protection
- file type validation
- duplicate document detection
- FAISS and metadata consistency checks
- rollback handling during failed processing and deletion
- LLM timeout handling
- query rewrite fallback
- citation grounding
- debug routes disabled by default

## Production Notes

The current storage design is suitable for a portfolio project and a single backend instance.

For a larger production deployment, the next improvements would be:

- move users, sessions, document metadata, and history to PostgreSQL
- use object storage for uploaded documents
- use persistent shared vector storage
- process large documents through a background job queue
- add rate limiting and refresh-token support
- add automated unit and integration tests
- add Docker and CI/CD
- add monitoring for latency, errors, token usage, and retrieval quality

## Available Commands

Backend syntax check:

```bash
python -m compileall -q app.py backend
```

Run retrieval evaluation:

```bash
python -m backend.eval.run_eval
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Frontend production build:

```bash
npm run build
```

## License

This project was built for learning, portfolio development, and interview preparation.
