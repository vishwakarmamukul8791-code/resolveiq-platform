# ResolveIQ — AI-Powered Incident Resolution Platform

[![CI](https://github.com/vishwakarmamukul8791-code/intelligent-incident-resolution-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/vishwakarmamukul8791-code/intelligent-incident-resolution-assistant/actions/workflows/ci.yml)

ResolveIQ is a full-stack Retrieval-Augmented Generation (RAG) platform for investigating IT incidents against an internal knowledge base. It combines lexical and semantic retrieval, confidence-aware answer generation, grounded citations, engineer history, and an admin operations dashboard.

## Live application

- Frontend: [resolveiq-five.vercel.app](https://resolveiq-five.vercel.app)
- Backend health: [resolveiq-api-8lmh.onrender.com/health](https://resolveiq-api-8lmh.onrender.com/health)
- Repository: [GitHub](https://github.com/vishwakarmamukul8791-code/intelligent-incident-resolution-assistant)

The Render Free backend can take up to a minute to wake after inactivity.

## What ResolveIQ does

- Authenticates admins and support engineers with JWT and role checks.
- Accepts PDF, CSV, and TXT knowledge-base documents.
- Extracts, cleans, chunks, embeds, and indexes document content.
- Combines BM25 and FAISS results with Reciprocal Rank Fusion (RRF).
- Optionally reranks candidates with a cross-encoder.
- Sends retrieved context to Gemini only when evidence passes confidence gating.
- Returns source document, page, and location citations.
- Tracks investigation threads, sessions, confidence distribution, and knowledge gaps.
- Gives admins document, engineer, analytics, and health controls.

## RAG pipeline

```text
Single incident question
        |
        v
Optional query rewrite (safe fallback to original)
        |
        +-----------------------+
        |                       |
        v                       v
BM25 lexical search      FAISS semantic search
        |                       |
        +-----------+-----------+
                    |
                    v
          Reciprocal Rank Fusion
                    |
                    v
        Optional cross-encoder rerank
                    |
                    v
       Retrieval-aware confidence gate
             /               \
            /                 \
       enough evidence       weak evidence
            |                     |
            v                     v
     grounded Gemini answer    safe abstention
            |
            v
   answer + citations + history
```

### Confidence safety contract

- RRF and cross-encoder scores use separate thresholds.
- A single weak retriever match stays Low confidence.
- Zero and negative BM25 scores are discarded before fusion.
- If Gemini returns its required no-information response, confidence is forced to Low and sources/supporting chunks are cleared.
- Multiple independent questions in one request return HTTP 422 with `Please ask one incident question at a time.` The current response model intentionally represents one incident answer and one confidence decision.

## Technology stack

| Area | Technology |
|---|---|
| Frontend | React 19, Vite, React Router |
| Backend | FastAPI, Python 3.12, Uvicorn |
| Answer generation | Google Gemini |
| Embeddings | Gemini in memory-constrained production; SentenceTransformers locally |
| Vector index | FAISS `IndexFlatL2` |
| Lexical retrieval | BM25 (`rank-bm25`) |
| Fusion | Reciprocal Rank Fusion |
| Optional reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Authentication | JWT HS256, PBKDF2-HMAC-SHA256 |
| Runtime state | JSON, uploaded files, and FAISS under `DATA_DIR` |
| Hosting | Vercel frontend, Render backend |

## Project structure

```text
.
|-- app.py
|-- Dockerfile
|-- requirements.txt
|-- requirements-render.txt
|-- .env.example
|-- .github/workflows/ci.yml
|-- backend/
|   |-- eval/
|   |-- routes/
|   `-- services/
|-- frontend/
|   |-- src/
|   |-- package.json
|   `-- vercel.json
`-- tests/
```

Runtime files are generated under `DATA_DIR` and ignored by Git:

```text
data/raw/                         uploaded source files
data/users.json                   user accounts
data/sessions.json                login sessions
data/document_registry.json       processed document registry
data/history/chat_history.json    investigation history
data/vector_store/index.faiss     vector index
data/vector_store/metadata.json   chunk metadata
```

## Local setup — Windows PowerShell

### 1. Clone and create the backend environment

```powershell
git clone https://github.com/vishwakarmamukul8791-code/intelligent-incident-resolution-assistant.git
Set-Location intelligent-incident-resolution-assistant

py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure backend environment

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value and your Gemini key in `.env`:

```env
ENVIRONMENT=development
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_generated_secret
DATA_DIR=data
FRONTEND_ORIGIN=
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=384
ENABLE_CROSS_ENCODER=true
ENABLE_DEBUG_ROUTES=false
MAX_UPLOAD_SIZE_MB=10
```

### 3. Create the first admin and start the API

```powershell
python -m backend.seed_admin
uvicorn app:app --reload
```

Local API endpoints:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

### 4. Start the frontend

Open a second PowerShell window:

```powershell
Set-Location intelligent-incident-resolution-assistant\frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

The frontend runs at `http://localhost:5173` and uses `VITE_API_BASE_URL=http://localhost:8000` by default.

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `GEMINI_API_KEY` | Yes | Gemini answer generation and Gemini embeddings |
| `JWT_SECRET_KEY` | Yes | JWT signing and verification |
| `ENVIRONMENT` | No | Use `production` to disable API docs and local CORS origins |
| `FRONTEND_ORIGIN` | Production | Comma-separated allowed frontend origins |
| `DATA_DIR` | No | Runtime state directory; defaults to repository `data/` |
| `EMBEDDING_PROVIDER` | No | `local` or `gemini` |
| `EMBEDDING_MODEL` | No | Gemini embedding model name |
| `EMBEDDING_DIMENSION` | No | Embedding/index dimension; defaults to 384 |
| `ENABLE_CROSS_ENCODER` | No | Disable on memory-constrained instances |
| `QUERY_REWRITE_ENABLED` | No | Enables an optional Gemini rewrite call |
| `ENABLE_DEBUG_ROUTES` | No | Development-only admin retrieval diagnostics |
| `MAX_UPLOAD_SIZE_MB` | No | Maximum PDF/CSV/TXT upload size; defaults to 10 |
| `BOOTSTRAP_ADMIN_USERNAME` | Deployment | Idempotent first-admin bootstrap username |
| `BOOTSTRAP_ADMIN_PASSWORD` | Deployment | First-admin bootstrap password; keep secret |
| `BOOTSTRAP_ADMIN_RESET_VERSION` | No | Change to intentionally reset the bootstrap admin password |

## Production persistence warning

ResolveIQ currently stores accounts, sessions, history, uploads, metadata, and FAISS state on the backend filesystem.

Render Free storage is ephemeral. A redeploy, restart, or instance replacement can remove all runtime state. `DATA_DIR` makes the storage location configurable; it does not make a Free filesystem persistent. The bootstrap variables can recreate the first admin, but they cannot restore uploaded documents or history.

For retained production state, use one of these approaches:

1. Attach a persistent Render disk, set `DATA_DIR` to its mount path (for example `/var/data`), and run one backend instance.
2. Move users/sessions/history to PostgreSQL, uploads to object storage, and vectors to a persistent vector store.

Do not treat the current Render Free deployment as durable storage.

## Docker

The production image uses the memory-efficient Render dependency set, Gemini embeddings, and disables the cross-encoder by default.

```powershell
docker build -t resolveiq-api .
docker run --rm -p 8000:8000 `
  -e ENVIRONMENT=production `
  -e GEMINI_API_KEY=your_key `
  -e JWT_SECRET_KEY=your_secret `
  -e FRONTEND_ORIGIN=http://localhost:5173 `
  -e BOOTSTRAP_ADMIN_USERNAME=admin `
  -e BOOTSTRAP_ADMIN_PASSWORD=replace_with_12_plus_chars `
  -v resolveiq-data:/app/data `
  resolveiq-api
```

## Validation and CI

Run the same core checks locally:

```powershell
python -m compileall -q app.py backend tests
python -m unittest discover -s tests -p "test_*.py" -v

Set-Location frontend
npm ci
npm run lint
npm run build
Set-Location ..
```

The GitHub Actions workflow runs three independent jobs on pushes and pull requests:

- backend compilation and unit tests
- frontend lint and production build
- backend Docker image build

Offline retrieval evaluation (requires an existing local corpus and index):

```powershell
python -m backend.eval.run_eval
```

## Main API endpoints

| Method | Endpoint | Access |
|---|---|---|
| POST | `/auth/login` | Public |
| POST | `/auth/logout` | Authenticated |
| POST | `/auth/reset-password` | Authenticated |
| GET | `/auth/me` | Authenticated |
| POST | `/ask` | Authenticated, password reset complete |
| GET | `/documents` | Authenticated, password reset complete |
| GET | `/document/{filename}` | Authenticated, password reset complete |
| GET/PATCH/DELETE | `/history...` | Authenticated, ownership scoped |
| POST | `/upload` | Admin |
| POST | `/process-document` | Admin |
| DELETE | `/document/{filename}` | Admin |
| GET | `/admin/system-health` | Admin |
| GET | `/debug/retrieval` | Admin, development-only when enabled |
| GET | `/health` | Public |
| GET | `/stats` | Public |

## Security and reliability controls

- Server-side current-user, active-status, role, and forced-password-reset checks
- PBKDF2 password hashing with per-user salts and constant-time verification
- Ownership checks for history and session mutations
- Filename/path traversal protection and file-content validation
- Streamed, size-bounded uploads with partial-file cleanup
- Atomic JSON and FAISS writes; corrupted JSON fails closed
- Serialized in-process state mutations and document index operations
- FAISS/metadata consistency checks and rollback paths
- Provider timeout/error mapping without exposing provider internals
- Retrieval-method-aware confidence gating and LLM abstention downgrade
- UTC timestamps with legacy naive-UTC display compatibility
- Production API docs and retrieval debug routes disabled by default

## Current deployment limits

- Local JSON/FAISS storage is designed for a single API instance, not horizontal scaling.
- Document processing is synchronous; large production workloads should use a background queue.
- JWT access tokens do not use refresh tokens or a revocation list. Active status and password-reset state are still checked on every protected request.
- Retrieval thresholds should be recalibrated whenever the embedding model, corpus, or reranker changes.

## License

Built as a portfolio and learning project for production-oriented RAG engineering.
