RELEVANCE_THRESHOLD = 0.0
HIGH_CONFIDENCE_THRESHOLD = 3.0


def calculate_confidence(reranked_results):

    if not reranked_results:
        return {
            "confidence": "Low",
            "top_score": None,
            "supporting_chunks": 0
        }

    top_score = reranked_results[0]["relevance_score"]

    supporting_chunks = sum(
        1 for result in reranked_results
        if result["relevance_score"] > RELEVANCE_THRESHOLD
    )

    if top_score >= HIGH_CONFIDENCE_THRESHOLD:
        confidence = "High"

    elif top_score >= RELEVANCE_THRESHOLD:
        confidence = "Medium"

    else:
        confidence = "Low"

    return {
        "confidence": confidence,
        "top_score": round(top_score, 3),
        "supporting_chunks": supporting_chunks
    }


def filter_relevant_chunks(reranked_results):

    return [
        result for result in reranked_results
        if result["relevance_score"] > RELEVANCE_THRESHOLD
    ]