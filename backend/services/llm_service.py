import os
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)


def build_prompt(question: str, context: str) -> str:

    prompt = f"""
### ROLE

You are an Intelligent Incident Resolution Assistant.

### OBJECTIVE

Help software engineers answer questions using the retrieved knowledge base.

### RULES

1. Use only the provided context.
2. Never fabricate information.
3. If the answer cannot be found in the provided context, respond exactly:

"I couldn't find this information in the uploaded documents."

4. Do not use your own knowledge.
5. Keep answers concise.
6. Use numbered steps where appropriate.

### CONTEXT

{context}

### QUESTION

{question}

### ANSWER
"""

    return prompt


def generate_answer(
    question,
    context
):

    prompt = build_prompt(
        question,
        context
    )

    response = model.generate_content(
        prompt
    )

    return response.text