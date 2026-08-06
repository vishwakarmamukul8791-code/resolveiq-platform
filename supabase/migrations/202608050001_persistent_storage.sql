begin;

create extension if not exists vector with schema extensions;

create table if not exists public.resolveiq_records (
    namespace text not null,
    record_key text not null,
    position integer not null check (position >= 0),
    payload jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (namespace, record_key),
    unique (namespace, position)
);

create index if not exists resolveiq_records_namespace_idx
    on public.resolveiq_records (namespace, position);

create table if not exists public.resolveiq_chunks (
    chunk_id uuid primary key,
    document_name text not null,
    chunk text not null,
    page_number integer,
    source_location text,
    embedding extensions.vector(384) not null,
    created_at timestamptz not null default now()
);

create index if not exists resolveiq_chunks_document_name_idx
    on public.resolveiq_chunks (document_name);

create index if not exists resolveiq_chunks_embedding_hnsw_idx
    on public.resolveiq_chunks
    using hnsw (embedding extensions.vector_cosine_ops);

alter table public.resolveiq_records enable row level security;
alter table public.resolveiq_chunks enable row level security;

revoke all on public.resolveiq_records from anon, authenticated;
revoke all on public.resolveiq_chunks from anon, authenticated;

insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
) values (
    'resolveiq-documents',
    'resolveiq-documents',
    false,
    10485760,
    array[
        'application/pdf',
        'text/plain',
        'text/csv',
        'application/vnd.ms-excel'
    ]
)
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

commit;
