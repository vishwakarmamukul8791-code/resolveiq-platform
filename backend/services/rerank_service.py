from sentence_transformers import CrossEncoder

_model = None


def _get_model():

    global _model

    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    return _model


def rerank(query, candidates, top_k=5):

    if not candidates:
        return []

    model = _get_model()

    pairs = [[query, candidate["chunk"]] for candidate in candidates]

    scores = model.predict(pairs)

    reranked = []

    for candidate, score in zip(candidates, scores):

        entry = candidate.copy()
        entry["rerank_score"] = float(score)
        reranked.append(entry)

    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

    return reranked[:top_k]