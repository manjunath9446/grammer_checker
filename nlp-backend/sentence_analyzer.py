from fastapi import HTTPException
from pydantic import BaseModel
from utils import correct_with_groq

class SentenceRequest(BaseModel):
    sentence: str

async def analyze_sentence(request: SentenceRequest):
    try:
        corrected = await correct_with_groq(request.sentence)
        return {"corrected_sentence": corrected}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
