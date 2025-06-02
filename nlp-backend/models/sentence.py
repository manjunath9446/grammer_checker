from pydantic import BaseModel

class SentenceRequest(BaseModel):
    sentence: str

class SentenceResponse(BaseModel):
    corrected: str
    explanation: str
    score: int
