# Supabase persistence deployment

This migration keeps the FastAPI authentication and RAG behavior while moving
durable state off Render's temporary filesystem:

- PostgreSQL JSONB records: users, sessions, history, and document registry
- PostgreSQL `pgvector`: document chunks and 384-dimensional embeddings
- private Supabase Storage: uploaded PDF, CSV, and TXT source files

The React frontend continues to use the FastAPI API. It never receives a
Supabase database password or service-role key.

## 1. Create the Supabase project

Create a Free project and store its database password in a password manager.
Do not put the password or any Supabase secret in Git, screenshots, issue
comments, or chat messages.

## 2. Apply the database migration

Open **SQL Editor** in the Supabase dashboard. Copy the complete contents of:

```text
supabase/migrations/202608050001_persistent_storage.sql
```

Run it once. The migration enables `pgvector`, creates the two application
tables and creates the private `resolveiq-documents` bucket.

The app intentionally does not create its own production schema at startup.
If this migration is missing, startup fails with a clear schema error instead
of silently falling back to temporary local files.

## 3. Collect the server-side connection values

From **Connect** in the Supabase dashboard, copy the **Session pooler**
connection string (IPv4, port 5432). Render Free should use this connection
instead of the IPv6-only direct connection.

Also copy these values from the Supabase project settings:

- Project URL
- service-role key (server secret, never a frontend variable)

## 4. Configure Render

Add or update these environment variables on the FastAPI service:

```text
PERSISTENCE_BACKEND=supabase
SUPABASE_DATABASE_URL=<Session pooler connection string>
SUPABASE_URL=<Project URL>
SUPABASE_SERVICE_ROLE_KEY=<server-only service-role key>
SUPABASE_STORAGE_BUCKET=resolveiq-documents
ENVIRONMENT=production
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=384
ENABLE_CROSS_ENCODER=false
```

Keep the existing values for:

```text
GEMINI_API_KEY
JWT_SECRET_KEY
FRONTEND_ORIGIN
BOOTSTRAP_ADMIN_USERNAME
BOOTSTRAP_ADMIN_PASSWORD
BOOTSTRAP_ADMIN_RESET_VERSION
```

Set Render's health-check path to:

```text
/health/live
```

`/health/live` checks that the API process is running. `/health` remains the
readiness endpoint and also checks PostgreSQL, pgvector, storage configuration,
Gemini configuration, and JWT configuration.

## 5. Deploy and verify

After the branch has passed CI and is merged, deploy it and verify in order:

1. `GET /health/live` returns HTTP 200 and `{"status":"alive"}`.
2. `GET /health` returns HTTP 200 and reports PostgreSQL connected,
   pgvector loaded, private storage configured, and overall status Healthy.
3. Sign in with the bootstrap administrator and change the temporary password.
4. Create one engineer account.
5. Upload and process one small TXT knowledge-base file.
6. Ask one question and confirm a citation and history entry are stored.
7. Trigger one manual Render redeploy.
8. Confirm the changed admin password, engineer, document, retrieval result,
   and history are all still present.

Do not change `BOOTSTRAP_ADMIN_RESET_VERSION` during the redeploy test. That
variable is an intentional emergency reset switch; changing it correctly
forces the bootstrap administrator back to the environment password.

## Data recovery note

State already erased by Render's temporary filesystem cannot be recovered
without a backup. The first Supabase deployment starts with a new durable
store, so documents and engineers that no longer exist must be recreated once.
