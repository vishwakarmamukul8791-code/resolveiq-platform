import os

from backend.services.llm_service import (
    LLMServiceError,
    generate_text
)
from backend.services.logging_service import log_error, log_info


DEFAULT_REWRITE_MODEL = "gemini-3.5-flash-lite"
DEFAULT_REWRITE_TIMEOUT_MS = 8_000
DEFAULT_REWRITE_MAX_OUTPUT_TOKENS = 256


REWRITE_PROMPT_TEMPLATE = """
Rewrite the following IT support question as one concise, keyword-rich
technical search query.

Preserve all error codes and technical identifiers exactly.
Do not answer the question.
Do not add facts.
Output only the rewritten query.

<original_question>
{question}
</original_question>
"""


def _is_query_rewrite_enabled() -> bool:
    value = os.getenv(
        "QUERY_REWRITE_ENABLED",
        "false"
    ).strip().lower()

    return value in {
        "1",
        "true",
        "yes",
        "on"
    }


def _read_rewrite_timeout_ms() -> int:
    raw_value = os.getenv(
        "GEMINI_REWRITE_TIMEOUT_MS",
        str(DEFAULT_REWRITE_TIMEOUT_MS)
    )

    try:
        timeout_ms = int(raw_value)
    except ValueError:
        log_error(
            "Invalid GEMINI_REWRITE_TIMEOUT_MS; "
            "using the default timeout."
        )
        return DEFAULT_REWRITE_TIMEOUT_MS

    if timeout_ms <= 0:
        log_error(
            "Invalid GEMINI_REWRITE_TIMEOUT_MS; "
            "using the default timeout."
        )
        return DEFAULT_REWRITE_TIMEOUT_MS

    return timeout_ms


def _get_rewrite_model_name() -> str:
    return (
        os.getenv(
            "GEMINI_REWRITE_MODEL",
            DEFAULT_REWRITE_MODEL
        ).strip()
        or DEFAULT_REWRITE_MODEL
    )


def rewrite_query(question: str) -> str:
    """
    Optionally rewrites a question for retrieval.

    Query rewriting is disabled by default because retrieval must not depend
    on a second provider request. Hybrid retrieval safely uses the original
    query when rewriting is disabled or unavailable.
    """

    if not question or not question.strip():
        return question

    original = question.strip()

    if not _is_query_rewrite_enabled():
        log_info(
            "Query rewrite disabled; using original query."
        )
        return original

    prompt = REWRITE_PROMPT_TEMPLATE.format(
        question=original
    )

    try:
        rewritten = generate_text(
            prompt=prompt,
            timeout_ms=_read_rewrite_timeout_ms(),
            model_name=_get_rewrite_model_name(),
            thinking_level="minimal",
            max_output_tokens=(
                DEFAULT_REWRITE_MAX_OUTPUT_TOKENS
            )
        )

        rewritten = rewritten.strip('"').strip("'").strip()

        if not rewritten:
            log_info(
                "Query rewrite returned empty output; "
                "using original query."
            )
            return original

        if rewritten.lower() == original.lower():
            log_info("Query rewrite made no change.")
        else:
            log_info("Query rewrite completed successfully.")

        return rewritten

    except LLMServiceError as exc:
        log_error(
            "Query rewrite failed; using original query. "
            f"category={exc.category}"
        )
        return original

    except Exception as exc:
        log_error(
            "Unexpected query rewrite failure; using original query. "
            f"type={type(exc).__name__}"
        )
        return original