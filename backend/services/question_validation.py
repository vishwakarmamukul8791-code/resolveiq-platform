"""
Shared "one question at a time" validation for /ask and /guest/ask.

Previously ask.py enforced this (reject a query containing more than one
"?") but guest.py's normalization only stripped whitespace and checked
for emptiness — the multi-question contract silently didn't apply to the
unauthenticated endpoint at all (P3-02). Both routes now call the same
function so the contract can't drift between them again.
"""

import re

from fastapi import HTTPException

MULTI_QUESTION_MESSAGE = "Please ask one incident question at a time."


def validate_single_question(raw_query: str) -> str:
    query = raw_query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty.",
        )

    normalized_question_marks = re.sub(r"\?+", "?", query)

    if normalized_question_marks.count("?") > 1:
        raise HTTPException(
            status_code=422,
            detail=MULTI_QUESTION_MESSAGE,
        )

    return query
