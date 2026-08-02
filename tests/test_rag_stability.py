import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.eval.run_eval import evaluate_abstain_path
from backend.routes.ask import (
    AskRequest,
    MULTI_QUESTION_MESSAGE,
    ask_question,
)
from backend.routes.debug_retrieval import debug_retrieval
from backend.services.bm25_service import search_bm25
from backend.services.llm_service import (
    NO_INFORMATION_ANSWER,
    is_no_information_answer,
)


def make_candidate(score=0.033):
    return {
        "chunk_id": "chunk-1",
        "document_name": "oauth-runbook.txt",
        "chunk": "Restart the affected service.",
        "page_number": 1,
        "source_location": "page 1",
        "rrf_score": score,
    }


class AskStabilityTests(unittest.TestCase):

    def test_multiple_questions_are_rejected_before_retrieval(self):
        with patch("backend.routes.ask.rewrite_query") as rewrite_mock:
            with self.assertRaises(HTTPException) as raised:
                ask_question(
                    payload=AskRequest(
                        query=(
                            "Why does OAuth fail? "
                            "How do we fix Kafka lag?"
                        ),
                    ),
                    current_user={"username": "mukul"},
                )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(
            raised.exception.detail,
            MULTI_QUESTION_MESSAGE,
        )
        rewrite_mock.assert_not_called()

    def test_repeated_question_marks_remain_one_question(self):
        candidate = make_candidate()

        with (
            patch(
                "backend.routes.ask.rewrite_query",
                return_value="why does oauth fail",
            ),
            patch(
                "backend.routes.ask.hybrid_search",
                return_value=[candidate],
            ),
            patch(
                "backend.routes.ask.rerank",
                return_value=[candidate],
            ),
            patch(
                "backend.routes.ask.generate_answer",
                return_value="The token expired.",
            ),
            patch("backend.routes.ask.append_history"),
            patch("backend.routes.ask.record_question"),
        ):
            response = ask_question(
                payload=AskRequest(query="Why does OAuth fail???"),
                x_session_id=None,
                current_user={"username": "mukul"},
            )

        self.assertEqual(response["confidence"], "High")

    def test_llm_abstention_downgrades_confidence_and_hides_sources(self):
        candidate = make_candidate()

        with (
            patch(
                "backend.routes.ask.rewrite_query",
                return_value="oauth token exchange failure",
            ),
            patch(
                "backend.routes.ask.hybrid_search",
                return_value=[candidate],
            ),
            patch(
                "backend.routes.ask.rerank",
                return_value=[candidate],
            ),
            patch(
                "backend.routes.ask.generate_answer",
                return_value=NO_INFORMATION_ANSWER,
            ),
            patch(
                "backend.routes.ask.append_history",
            ) as append_history_mock,
            patch(
                "backend.routes.ask.record_question",
            ) as record_question_mock,
        ):
            response = ask_question(
                payload=AskRequest(
                    query="Why does OAuth token exchange fail?",
                ),
                x_session_id="test-session",
                current_user={"username": "mukul"},
            )

        self.assertEqual(response["answer"], NO_INFORMATION_ANSWER)
        self.assertEqual(response["confidence"], "Low")
        self.assertEqual(response["sources"], [])
        self.assertEqual(response["supporting_chunks"], 0)
        self.assertEqual(response["top_relevance_score"], 0.033)
        record_question_mock.assert_called_once_with(
            "test-session",
            "Low",
            "mukul",
        )

        saved_entry = append_history_mock.call_args.args[0]
        self.assertEqual(saved_entry["confidence"], "Low")
        self.assertEqual(saved_entry["sources"], [])


class RetrievalStabilityTests(unittest.TestCase):

    def test_bm25_discards_zero_and_negative_scores(self):
        metadata = [
            {
                "chunk_id": "chunk-1",
                "document_name": "one.txt",
                "chunk": "unrelated content",
            },
            {
                "chunk_id": "chunk-2",
                "document_name": "two.txt",
                "chunk": "other unrelated content",
            },
        ]

        with (
            patch(
                "backend.services.bm25_service.load_metadata",
                return_value=metadata,
            ),
            patch(
                "backend.services.bm25_service.BM25Okapi",
            ) as bm25_class,
        ):
            bm25_class.return_value.get_scores.return_value = [
                0.0,
                -0.25,
            ]
            results = search_bm25("who is mukul")

        self.assertEqual(results, [])

    def test_debug_route_uses_normalized_retrieval_method(self):
        candidate = make_candidate()

        with (
            patch(
                "backend.routes.debug_retrieval.search_similar_chunks",
                return_value=([candidate], None),
            ),
            patch(
                "backend.routes.debug_retrieval.search_bm25",
                return_value=[candidate],
            ),
            patch(
                "backend.routes.debug_retrieval.hybrid_search",
                return_value=[candidate],
            ),
            patch(
                "backend.routes.debug_retrieval.rerank",
                return_value=[candidate],
            ),
        ):
            result = debug_retrieval(
                query="Why does OAuth fail?",
                rewritten_query="oauth failure",
                current_user={"username": "admin"},
            )

        self.assertEqual(result["final_confidence"]["confidence"], "High")

    def test_eval_abstain_path_uses_normalized_retrieval_method(self):
        candidate = make_candidate(score=1 / 61)

        with (
            patch(
                "backend.eval.run_eval.NEGATIVE_CASES",
                [{"id": "negative-1", "query": "who is mukul"}],
            ),
            patch(
                "backend.eval.run_eval.hybrid_search",
                return_value=[candidate],
            ),
            patch(
                "backend.eval.run_eval.rerank",
                return_value=[candidate],
            ),
        ):
            result = evaluate_abstain_path()

        self.assertEqual(result["abstain_accuracy"], 1.0)


class LLMStabilityTests(unittest.TestCase):

    def test_abstention_detector_accepts_quotes_and_whitespace(self):
        answer = f'  "{NO_INFORMATION_ANSWER}"\n'

        self.assertTrue(is_no_information_answer(answer))
        self.assertFalse(
            is_no_information_answer(
                "The OAuth token expired.",
            )
        )


if __name__ == "__main__":
    unittest.main()
