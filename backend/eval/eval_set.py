"""
Offline retrieval evaluation dataset.

Every query and marker here is grounded in the real corpus text as of this
handoff: Sample_Incidents_Extended.txt (INC-1009 to INC-1020) and the two KB
articles. If the corpus changes (new incidents added, INC-1001-1008 restored,
etc.), this file needs a matching update — it is NOT auto-derived from the
corpus, it's a hand-built ground truth.

expected_markers: a list of substrings (matched case-insensitively against
retrieved chunk text). A case counts as a HIT if ANY marker is found in a
retrieved chunk. Multiple markers are used deliberately where more than one
document legitimately answers the same query (e.g. an incident AND the KB
article covering the same root cause both count as correct — see INC-1019
and INC-1010 below).

Note on chunking: chunks are plain 500-char / 100-char-overlap character
windows (see backend/routes/process.py::_chunk_single_text), not
sentence-aware. It's possible for a marker to land exactly on a chunk
boundary and get split across two chunks in a way that clips it in both. If
a case fails, check that before assuming the retrieval method itself is at
fault — it can be a chunking artifact worth knowing about either way.

Two tiers of cases:
- INC-1009 through KB-AUTH-01: the original 14, each written to match its
  target incident closely. First real run scored a flat 1.000 across all
  four retrieval methods — a ceiling effect, not proof hybrid/reranking
  help, since the corpus is small and every topic is orthogonal enough
  that even the weakest method aces it.
- HARD-01 through HARD-07: added specifically to break that ceiling.
  These use real distractor wording pulled from a DIFFERENT incident's
  vocabulary, or fully paraphrase the symptom with zero literal token
  overlap with the target chunk. If the four methods are ever going to
  diverge, it should show up here — read the per_case rank data for these,
  not just the aggregate hit rate.
"""

EVAL_CASES = [
    {
        "id": "INC-1009",
        "query": "Getting ORA-12154 when the app tries to connect to Oracle after we migrated the DB server, any idea?",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["ORA-12154"],
    },
    {
        "id": "INC-1010",
        "query": "Postgres connections are being refused from the app tier right after someone changed a config file.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["SQLSTATE[08001]", "pg_hba.conf"],
    },
    {
        "id": "INC-1011",
        "query": "Our Node backend keeps throwing ECONNREFUSED calling the payments service, like nothing is listening.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["ECONNREFUSED"],
    },
    {
        "id": "INC-1012",
        "query": "The order-processing pod keeps restarting, stuck in CrashLoopBackOff, what should I check?",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["CrashLoopBackOff"],
    },
    {
        "id": "INC-1013",
        "query": "Partners are getting 429 Too Many Requests from our public API, why?",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["HTTP 429", "Too Many Requests"],
    },
    {
        "id": "INC-1014",
        "query": "Dashboard users are seeing SSL_ERROR_BAD_CERT_DOMAIN in the browser and can't load the page.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["SSL_ERROR_BAD_CERT_DOMAIN"],
    },
    {
        "id": "INC-1015",
        "query": "Services intermittently can't resolve the auth service hostname, getting SERVFAIL from DNS.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["SERVFAIL"],
    },
    {
        "id": "INC-1016",
        "query": "The nightly batch reporting job is crashing with a Java heap OutOfMemoryError.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["OutOfMemoryError"],
    },
    {
        "id": "INC-1017",
        "query": "Kafka consumers on order-events are falling way behind, lag is climbing into the millions.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["order-events"],
    },
    {
        "id": "INC-1018",
        "query": "File uploads are failing with disk quota exceeded errors, but we haven't changed any storage limits.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["disk quota exceeded"],
    },
    {
        "id": "INC-1019",
        "query": "Nobody in the company can log in, identity provider is returning invalid_grant during OAuth.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["invalid_grant", "NTP", "clock drift"],
    },
    {
        "id": "INC-1020",
        "query": "Customer portal users are getting intermittent 502 Bad Gateway errors during busy hours.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["HTTP 502", "Bad Gateway"],
    },
    {
        "id": "KB-DB-01",
        "query": "How do I troubleshoot SQL Server named instance connection problems and the SQL Server Browser service?",
        "expected_document": "KB_Database_Connectivity_Troubleshooting.txt",
        "expected_markers": ["SQL Server Browser", "UDP port 1434"],
    },
    {
        "id": "KB-AUTH-01",
        "query": "A brand new employee's account was created but they still can't access the system, what could be missing?",
        "expected_document": "KB_Authentication_Access_Troubleshooting.txt",
        "expected_markers": ["security groups", "gpupdate"],
    },

    # --- Harder cases added after the first eval run came back a flat 1.000
    # across all four methods (ceiling effect — the original 14 cases were
    # too topically orthogonal to create any competition between methods).
    # These use deliberate distractor wording: real red-herring vocabulary
    # from a DIFFERENT incident, so a weaker method has an actual chance to
    # get pulled toward the wrong chunk. A method that still lands the
    # correct marker at rank 1 despite the distractor is a genuinely
    # stronger result than acing the easy cases above.

    {
        # Genuinely ambiguous by design: both incidents are "config change
        # -> can't connect" stories. Either is a legitimate answer, so this
        # is scored as a hit if EITHER shows up, but the real signal is
        # which one each method puts at rank 1 — check per_case in the
        # output, don't just read the aggregate hit rate for this one.
        "id": "HARD-01-ambiguous-db",
        "query": "We changed something in our database configuration recently and now client apps can't establish new connections at all.",
        "expected_document": None,
        "expected_markers": ["ORA-12154", "SQLSTATE[08001]"],
    },
    {
        # Distractor: mentions a DB migration (INC-1009's context) but the
        # actual symptom described is the SSL cert issue from INC-1014.
        "id": "HARD-02-ssl-vs-db-migration",
        "query": "After we rotated TLS certificates last night, users are getting a browser security warning loading the dashboard — is this related to the recent database migration?",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["SSL_ERROR_BAD_CERT_DOMAIN"],
    },
    {
        # Distractor: mentions Kafka/buffering (INC-1017's context) but the
        # actual symptom described is the batch job heap OOM from INC-1016.
        "id": "HARD-03-oom-vs-kafka",
        "query": "Our nightly job died again with an out of memory crash — could this be a Kafka consumer lag issue causing it to buffer too much data?",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["OutOfMemoryError"],
    },
    {
        # Distractor: mentions rate limiting (INC-1013's context) but the
        # actual symptom described is the 502s from INC-1020.
        "id": "HARD-04-502-vs-ratelimit",
        "query": "We're seeing intermittent 5xx errors from the customer portal during busy hours — might this be a rate limiting issue since traffic has been high?",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["HTTP 502", "Bad Gateway"],
    },
    {
        # Pure symptom paraphrase, no error code, no product names — tests
        # whether retrieval still finds INC-1019 without any literal
        # token overlap with "invalid_grant" or "NTP".
        "id": "HARD-05-auth-paraphrase",
        "query": "Employees who could log in fine yesterday suddenly can't get past login this morning, and it seems to be affecting everyone around the same time.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["invalid_grant", "NTP", "clock drift"],
    },
    {
        # Pure symptom paraphrase for KB-only content — no incident is
        # this specific, tests general troubleshooting-guide retrieval
        # under vague phrasing rather than a direct topic match.
        "id": "HARD-06-sqlserver-paraphrase",
        "query": "One specific SQL Server instance won't accept remote connections even though the default instance is reachable fine — what should I check on the discovery side?",
        "expected_document": "KB_Database_Connectivity_Troubleshooting.txt",
        "expected_markers": ["SQL Server Browser", "UDP port 1434"],
    },
    {
        # Zero literal token overlap with "ECONNREFUSED", "Node", or
        # "payments" — specifically stresses BM25's weak spot (it can only
        # match tokens that are actually there) versus semantic search.
        "id": "HARD-07-econnrefused-paraphrase",
        "query": "Our checkout backend calls are bouncing back instantly, like nothing is bound to that port on the other side — same target service worked fine yesterday.",
        "expected_document": "Sample_Incidents_Extended.txt",
        "expected_markers": ["ECONNREFUSED"],
    },
]


# Queries with no correct answer in the corpus at all. These test the
# abstention path: confidence should remain Low, and /ask
# should never reach the LLM for these.
NEGATIVE_CASES = [
    {
        "id": "NEG-01",
        "query": "How do I reset my office printer to factory settings?",
    },
    {
        "id": "NEG-02",
        "query": "What's the company's PTO policy for new hires?",
    },
    {
        "id": "NEG-03",
        "query": "Can you recommend a good Italian restaurant near the office?",
    },
]