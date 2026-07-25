from backend.services.llm_service import model
from backend.services.logging_service import log_info, log_error


REWRITE_PROMPT_TEMPLATE = """
### ROLE

You rewrite IT support questions into clear, keyword-rich search queries for a
retrieval system indexing incident tickets and KB articles.

### RULES

1. Preserve every error code, status code, and technical identifier EXACTLY as
   written (e.g. ORA-12154, SQLSTATE[08001], ECONNREFUSED, CrashLoopBackOff,
   HTTP 429). Never alter, translate, retype, or "correct" these.
2. Fix typos and vague or conversational phrasing into concise technical
   language a support engineer would search with.
3. Do not answer the question. Do not add facts or assumptions that aren't
   implied by the original question.
4. If the original question is already clear and keyword-rich, return it
   unchanged.
5. Output ONLY the rewritten query on a single line. No explanation, no
   quotes, no prefix like "Rewritten query:".

### ORIGINAL QUESTION

{question}

### REWRITTEN QUERY
"""


def rewrite_query(question: str) -> str:
    """
    Rewrites a raw user question into a cleaner search query for retrieval.

    Reuses the same Gemini model instance as llm_service.py (one configured
    model, one place to change it later) rather than standing up a second
    genai.configure()/GenerativeModel().

    This is retrieval-only: the ORIGINAL question is still what's shown to
    the user, stored in history, and passed to generate_answer() for the
    final response. Only the search step uses the rewritten version.

    Falls back to the original question on empty output or any exception,
    so a rewrite failure can never block retrieval or take down /ask.
    """

    if not question or not question.strip():
        return question

    original = question.strip()
    prompt = REWRITE_PROMPT_TEMPLATE.format(question=original)

    try:
        response = model.generate_content(prompt)
        rewritten = (response.text or "").strip()

        # Defensive: the prompt forbids wrapping quotes, but LLM output isn't
        # guaranteed to comply — strip them rather than let them corrupt search.
        rewritten = rewritten.strip('"').strip("'").strip()

        if not rewritten:
            log_info("Query rewrite returned empty output — using original query.")
            return original

        if rewritten.lower() == original.lower():
            log_info(f"Query rewrite made no change: '{original}'")
        else:
            log_info(f"Query rewritten: '{original}' -> '{rewritten}'")

        return rewritten

    except Exception as e:
        log_error(f"Query rewrite failed, falling back to original query: {e}")
        return original