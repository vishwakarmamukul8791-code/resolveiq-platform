from backend.services.retrieval_service import (search_similar_chunks,get_context)  
from backend.services.llm_service import (generate_answer)  
from fastapi import APIRouter

router = APIRouter()


@router.get("/ask")
def ask_question(query: str):

    results = search_similar_chunks(
        query
    )
    print("========== RESULTS ==========")

    for result in results:
        print(result)
        print("=============================")




    context = get_context(
        results
    )
    print("========== CONTEXT ==========")
    print(context)
    print("=============================")
    answer = generate_answer(
    query,
    context
)

    sources = []

    for result in results:

        if result["document_name"] not in sources:

            sources.append(
                result["document_name"]
        )

    return {
    "question": query,
    "answer": answer,
    "sources": sources
}


