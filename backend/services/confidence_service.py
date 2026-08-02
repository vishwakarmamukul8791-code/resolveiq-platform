from math import isfinite


METHOD_THRESHOLDS = {
    "reranked": {
        "relevance": 0.0,
        "high": 3.0,
    },
    "hybrid": {
        "relevance": 0.02,
        "high": 0.03,
    },
}


def _read_score(result):
    try:
        score = float(result["relevance_score"])
    except (KeyError, TypeError, ValueError):
        return None

    if not isfinite(score):
        return None

    return score


def filter_relevant_chunks(results, method):
    thresholds = METHOD_THRESHOLDS.get(method)

    if thresholds is None:
        return []

    relevant_chunks = []

    for result in results:
        score = _read_score(result)

        if (
            score is not None
            and score > thresholds["relevance"]
        ):
            relevant_chunks.append(result)

    return relevant_chunks


def calculate_confidence(results, method):
    if not results:
        return {
            "confidence": "Low",
            "top_score": None,
            "supporting_chunks": 0,
        }

    top_score = _read_score(results[0])
    thresholds = METHOD_THRESHOLDS.get(method)

    if top_score is None or thresholds is None:
        return {
            "confidence": "Low",
            "top_score": (
                round(top_score, 3)
                if top_score is not None
                else None
            ),
            "supporting_chunks": 0,
        }

    relevant_chunks = filter_relevant_chunks(
        results,
        method,
    )

    if not relevant_chunks:
        confidence = "Low"
    elif top_score >= thresholds["high"]:
        confidence = "High"
    else:
        confidence = "Medium"

    return {
        "confidence": confidence,
        "top_score": round(top_score, 3),
        "supporting_chunks": len(relevant_chunks),
    }