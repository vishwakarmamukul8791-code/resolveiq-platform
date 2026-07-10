from fastapi import APIRouter
from datetime import datetime
from backend.services.logging_service import log_info
from backend.services.retrieval_service import (
    search_similar_chunks,
    get_context
)

from backend.services.llm_service import (
    generate_answer
)

from backend.services.history_service import (
    load_history,
    save_history
)
from backend.services.confidence_service import (
    calculate_confidence
)
from fastapi import HTTPException
from backend.services.logging_service import log_error


router = APIRouter()


@router.get("/ask")

def ask_question(
    
    query: str,
    document_name: str | None = None
):
    try:

        log_info(f"Question Received: {query}")

        results, distances = search_similar_chunks(query, document_name)

        context = get_context(results)

        answer = generate_answer(
            query,
            context
        )

        confidence, average_distance = calculate_confidence(
            distances
        )
    

        sources = []

        for result in results:

            if result["document_name"] not in sources:

                sources.append(
                    result["document_name"]
            )

        history = load_history()

        history.append(
        {
            "question": query,
            "answer": answer,
            "created_at": datetime.now().isoformat()
        }
    )

        save_history(history)
        log_info("Answer generated successfully.")

        return {
    "question": query,
    "answer": answer,
    "sources": sources,
    "confidence": confidence,
    "average_distance": average_distance
   }
    except Exception as e:

        log_error(str(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to generate answer."
        )