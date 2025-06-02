import os
import httpx
import re
from dotenv import load_dotenv

load_dotenv()

client = httpx.AsyncClient()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def analyze_sentence_with_groq(sentence: str) -> dict:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a grammar and tense expert. When a user sends a sentence, "
                    "return a corrected version of the sentence, give a grammar score out of 10, "
                    "and briefly explain what was wrong and why. Format the result as:\n"
                    "**Corrected sentence:** <corrected>\n"
                    "**Grammar score:** <score>\n"
                    "**Explanation:** <explanation>"
                ),
            },
            {"role": "user", "content": sentence},
        ],
    }

    response = await client.post(GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    assistant_message = data["choices"][0]["message"]["content"]

    # Use regex to extract sections
    corrected_match = re.search(r"\*\*Corrected sentence:\*\*\s*(.+)", assistant_message)
    score_match = re.search(r"\*\*Grammar score:\*\*\s*(.+)", assistant_message)
    explanation_match = re.search(r"\*\*Explanation:\*\*\s*(.+)", assistant_message, re.DOTALL)

    return {
        "corrected": corrected_match.group(1).strip() if corrected_match else "",
        "score": score_match.group(1).strip() if score_match else "",
        "explanation": explanation_match.group(1).strip() if explanation_match else "",
    }
