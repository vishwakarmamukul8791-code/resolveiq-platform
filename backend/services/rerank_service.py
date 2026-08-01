import os


_model = None


def _cross_encoder_enabled():
    return (
        os.getenv(
            "ENABLE_CROSS_ENCODER",
            "true"
        ).strip().lower()
        in {"1", "true", "yes"}
    )


def _get_model():
    global _model

    if _model is None:
        from sentence_transformers import CrossEncoder

        _model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

    return _model


def rerank(query, candidates, top_k=5):
    if not candidates:
        return []

    if not _cross_encoder_enabled():
        return [
            candidate.copy()
            for candidate in candidates[:top_k]
        ]

    model = _get_model()

    pairs = [
        [query, candidate["chunk"]]
        for candidate in candidates
    ]

    scores = model.predict(pairs)

    reranked = []

    for candidate, score in zip(candidates, scores):
        entry = candidate.copy()
        entry["rerank_score"] = float(score)
        reranked.append(entry)

    reranked.sort(
        key=lambda item: item["rerank_score"],
        reverse=True,
    )

    return reranked[:top_k]
