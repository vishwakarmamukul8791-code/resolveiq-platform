"""
Offline retrieval evaluation.

Runs predefined evaluation cases against semantic retrieval, BM25, hybrid
RRF, and hybrid retrieval with reranking. It reports Hit@1, Hit@5, and MRR@5,
then checks negative cases through the same retrieval and confidence path used
by /ask.

The evaluation is read-only. It uses the existing FAISS index, BM25 corpus,
and metadata without modifying or reprocessing documents.
"""

import json
import os
from datetime import datetime, timezone

from backend.services.retrieval_service import search_similar_chunks
from backend.services.bm25_service import search_bm25
from backend.services.hybrid_retrieval_service import hybrid_search
from backend.services.rerank_service import rerank
from backend.services.retrieval_contract import build_retrieval_response
from backend.services.confidence_service import calculate_confidence
from backend.services.logging_service import log_info
from backend.services.storage_paths import data_path

from backend.eval.eval_set import EVAL_CASES, NEGATIVE_CASES

TOP_K = 5
RESULTS_PATH = data_path("eval", "eval_results.json")


def _is_hit(chunk_text: str, markers: list) -> bool:

    text_lower = chunk_text.lower()

    return any(marker.lower() in text_lower for marker in markers)


def _first_hit_rank(chunks: list, markers: list) -> int:
    """1-indexed rank of the first chunk containing any marker, or 0 if none do."""

    for rank, chunk in enumerate(chunks, start=1):

        if _is_hit(chunk["chunk"], markers):
            return rank

    return 0


def _run_semantic(query, top_k):

    results, _ = search_similar_chunks(query, top_k=top_k)

    return results


def _run_bm25(query, top_k):

    return search_bm25(query, top_k=top_k)


def _run_hybrid(query, top_k):

    return hybrid_search(query, top_k=top_k, candidate_pool_size=10)


def _run_hybrid_reranked(query, top_k):

    candidates = hybrid_search(query, top_k=10, candidate_pool_size=10)

    return rerank(query, candidates, top_k=top_k)


# Order matters for the printed report, from baseline to full pipeline.
# so the improvement from hybrid and reranking reads top-to-bottom.
METHODS = {
    "semantic": _run_semantic,
    "bm25": _run_bm25,
    "hybrid (RRF)": _run_hybrid,
    "hybrid + reranked": _run_hybrid_reranked,
}


def evaluate_method(method_fn):

    hits_at_1 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    per_case = []

    for case in EVAL_CASES:

        results = method_fn(case["query"], TOP_K)

        rank = _first_hit_rank(results, case["expected_markers"])

        hit_5 = rank > 0
        hit_1 = rank == 1

        hits_at_5 += int(hit_5)
        hits_at_1 += int(hit_1)
        reciprocal_ranks.append(1 / rank if rank > 0 else 0.0)

        per_case.append({
            "id": case["id"],
            "query": case["query"],
            "hit": hit_5,
            "rank": rank if rank > 0 else None
        })

    total = len(EVAL_CASES)

    return {
        "hit_at_1": round(hits_at_1 / total, 3),
        "hit_at_5": round(hits_at_5 / total, 3),
        "mrr_at_5": round(sum(reciprocal_ranks) / total, 3),
        "per_case": per_case
    }


def evaluate_abstain_path():

    correct = 0
    per_case = []

    for case in NEGATIVE_CASES:

        candidates = hybrid_search(case["query"], top_k=10, candidate_pool_size=10)
        reranked = rerank(case["query"], candidates, top_k=5)
        normalized = build_retrieval_response(case["query"], reranked)
        reranked_results = [
            chunk.model_dump()
            for chunk in normalized.results
        ]

        confidence_info = calculate_confidence(
            reranked_results,
            method=normalized.method,
        )

        correctly_abstained = confidence_info["confidence"] == "Low"

        correct += int(correctly_abstained)

        per_case.append({
            "id": case["id"],
            "query": case["query"],
            "confidence": confidence_info["confidence"],
            "correctly_abstained": correctly_abstained
        })

    total = len(NEGATIVE_CASES)

    return {
        "abstain_accuracy": round(correct / total, 3) if total else None,
        "per_case": per_case
    }


def print_report(method_results, abstain_results):

    print("\n" + "=" * 62)
    print("RAG EVALUATION REPORT")
    print("=" * 62)
    print(f"{'Method':<20}{'Hit@1':>12}{'Hit@5':>12}{'MRR@5':>12}")
    print("-" * 62)

    for method_name, result in method_results.items():

        print(
            f"{method_name:<20}"
            f"{result['hit_at_1']:>12.3f}"
            f"{result['hit_at_5']:>12.3f}"
            f"{result['mrr_at_5']:>12.3f}"
        )

    print("-" * 62)
    print(f"Positive eval cases: {len(EVAL_CASES)}")

    print("\nAbstain path (negative queries should remain Low confidence):")

    abstain_pct = (
        abstain_results["abstain_accuracy"] * 100
        if abstain_results["abstain_accuracy"] is not None
        else 0
    )

    print(f"  Correctly abstained: {abstain_pct:.0f}% of {len(NEGATIVE_CASES)} cases")

    for case in abstain_results["per_case"]:

        status = "OK" if case["correctly_abstained"] else "FAILED"

        print(f"    [{status}] {case['id']}: confidence={case['confidence']}")

    print("=" * 62 + "\n")


def main():

    method_results = {}

    for method_name, method_fn in METHODS.items():

        print(f"Running: {method_name} ...")

        method_results[method_name] = evaluate_method(method_fn)

    print("Running: abstain path (negative queries) ...")

    abstain_results = evaluate_abstain_path()

    print_report(method_results, abstain_results)

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)

    output = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "methods": method_results,
        "abstain": abstain_results
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    log_info(f"Eval run complete, results saved to {RESULTS_PATH}")

    print(f"Full results (including per-case detail) saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
