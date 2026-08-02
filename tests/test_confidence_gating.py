import unittest
from unittest.mock import patch

from backend.routes.ask import (
    AskRequest,
    NO_MATCH_MESSAGE,
    ask_question,
)
from backend.services.confidence_service import (
    calculate_confidence,
    filter_relevant_chunks,
)


def make_results(*scores):
    return [
        {"relevance_score": score}
        for score in scores
    ]


class ConfidenceServiceTests(unittest.TestCase):

    def test_empty_results_are_low_confidence(self):
        result = calculate_confidence(
            [],
            method="hybrid",
        )

        self.assertEqual(result["confidence"], "Low")
        self.assertIsNone(result["top_score"])
        self.assertEqual(result["supporting_chunks"], 0)

    def test_single_retriever_rrf_score_is_rejected(self):
        results = make_results(1 / 61)

        confidence = calculate_confidence(
            results,
            method="hybrid",
        )
        relevant = filter_relevant_chunks(
            results,
            method="hybrid",
        )

        self.assertEqual(confidence["confidence"], "Low")
        self.assertEqual(confidence["top_score"], 0.016)
        self.assertEqual(confidence["supporting_chunks"], 0)
        self.assertEqual(relevant, [])

    def test_dual_retriever_rrf_score_can_be_medium(self):
        results = make_results(
            0.029,
            0.016,
        )

        confidence = calculate_confidence(
            results,
            method="hybrid",
        )

        self.assertEqual(confidence["confidence"], "Medium")
        self.assertEqual(confidence["supporting_chunks"], 1)

    def test_strong_rrf_agreement_is_high_confidence(self):
        confidence = calculate_confidence(
            make_results(0.033, 0.029),
            method="hybrid",
        )

        self.assertEqual(confidence["confidence"], "High")
        self.assertEqual(confidence["supporting_chunks"], 2)

    def test_cross_encoder_uses_reranked_thresholds(self):
        low = calculate_confidence(
            make_results(-0.1),
            method="reranked",
        )
        medium = calculate_confidence(
            make_results(1.5),
            method="reranked",
        )
        high = calculate_confidence(
            make_results(3.0),
            method="reranked",
        )

        self.assertEqual(low["confidence"], "Low")
        self.assertEqual(medium["confidence"], "Medium")
        self.assertEqual(high["confidence"], "High")

    def test_unknown_method_fails_closed(self):
        confidence = calculate_confidence(
            make_results(100.0),
            method="unknown",
        )
        relevant = filter_relevant_chunks(
            make_results(100.0),
            method="unknown",
        )

        self.assertEqual(confidence["confidence"], "Low")
        self.assertEqual(confidence["supporting_chunks"], 0)
        self.assertEqual(relevant, [])

    def test_invalid_score_fails_closed(self):
        confidence = calculate_confidence(
            make_results(float("nan")),
            method="hybrid",
        )

        self.assertEqual(confidence["confidence"], "Low")
        self.assertIsNone(confidence["top_score"])
        self.assertEqual(confidence["supporting_chunks"], 0)

    def test_ask_abstains_for_weak_hybrid_match(self):
        weak_candidate = {
            "chunk_id": "chunk-1",
            "document_name": "irrelevant.txt",
            "chunk": "This chunk does not answer the question.",
            "page_number": None,
            "source_location": None,
            "rrf_score": 1 / 61,
        }

        with (
            patch(
                "backend.routes.ask.rewrite_query",
                return_value="who is mukul",
            ),
            patch(
                "backend.routes.ask.hybrid_search",
                return_value=[weak_candidate],
            ),
            patch(
                "backend.routes.ask.rerank",
                return_value=[weak_candidate],
            ),
            patch(
                "backend.routes.ask.append_history",
            ) as append_history_mock,
            patch(
                "backend.routes.ask.record_question",
            ) as record_question_mock,
            patch(
                "backend.routes.ask.generate_answer",
            ) as generate_answer_mock,
        ):
            response = ask_question(
                payload=AskRequest(
                    query="who is mukul",
                ),
                x_session_id="test-session",
                current_user={
                    "username": "mukul",
                },
            )

        self.assertEqual(response["confidence"], "Low")
        self.assertEqual(response["sources"], [])
        self.assertEqual(response["supporting_chunks"], 0)
        self.assertEqual(response["top_relevance_score"], 0.016)
        self.assertEqual(response["answer"], NO_MATCH_MESSAGE)

        generate_answer_mock.assert_not_called()
        record_question_mock.assert_called_once_with(
            "test-session",
            "Low",
            "mukul",
        )

        saved_entry = append_history_mock.call_args.args[0]

        self.assertEqual(
            saved_entry["confidence"],
            "Low",
        )


if __name__ == "__main__":
    unittest.main()
