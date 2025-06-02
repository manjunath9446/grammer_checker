from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO
from docx import Document
import httpx
import os
import random
from dotenv import load_dotenv
from services.grammar_checker import analyze_sentence_with_groq

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SCHEMAS ===
class SentenceRequest(BaseModel):
    sentence: str

class SentenceResponse(BaseModel):
    corrected: str
    score: str
    explanation: str

class ChatRequest(BaseModel):
    message: str

class GrammarWord(BaseModel):
    term: str
    definition: str
    example: str
    relevance: str
    tip: str

# === ENDPOINTS ===

@app.get("/")
def read_root():
    return {"message": "Grammar Assistant API is running 🚀"}

# ✅ Sentence grammar analysis
@app.post("/analyze-sentence", response_model=SentenceResponse)
async def analyze_sentence(request: SentenceRequest):
    try:
        result = await analyze_sentence_with_groq(request.sentence)
        return SentenceResponse(**result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ✅ Chat-style grammar coach endpoint
@app.post("/grammar-coach-chat")
async def grammar_coach_chat(request: ChatRequest):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = f"""
You are a friendly English Grammar Coach. Explain grammar concepts in a simple, helpful way with headings, bullet points, and examples. Be beginner-friendly and suitable for IELTS and TOEFL learners.

User: {request.message}
"""

        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a helpful grammar coach."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()

            if "choices" in data:
                reply = data["choices"][0]["message"]["content"]
                return {"reply": reply}
            else:
                return JSONResponse(content={"error": "Invalid response from Groq API"}, status_code=500)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ✅ Document Upload for Correction
@app.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename.endswith(".docx"):
        doc = Document(BytesIO(content))

        for para in doc.paragraphs:
            corrected = await correct_with_groq(para.text.strip())
            para.text = corrected

        output = BytesIO()
        doc.save(output)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            headers={'Content-Disposition': 'attachment; filename="corrected_document.docx"'}
        )

    elif file.filename.endswith(".txt"):
        text = content.decode("utf-8")
        corrected = await correct_with_groq(text)

        output = BytesIO(corrected.encode("utf-8"))
        output.seek(0)

        return StreamingResponse(
            output,
            media_type='text/plain',
            headers={'Content-Disposition': 'attachment; filename="corrected_document.txt"'}
        )

    return JSONResponse(content={"error": "Unsupported file format."}, status_code=400)

# === Groq Correction Helper ===
async def correct_with_groq(text: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that corrects grammar mistakes."},
            {"role": "user", "content": f"Correct the grammar of this text: {text}"}
        ],
        "temperature": 0.3
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"].strip()
        else:
            return f"[Error] Groq API: {data.get('error', {}).get('message', 'Unexpected response')}"

# ✅ Daily Grammar Words Generator
word_pool = [

    {
      "term": "Cacophony",
      "definition": "A harsh, discordant mixture of sounds.",
      "example": "The cacophony of honking horns filled the street.",
      "relevance": "Impressive for descriptive writing.",
      "tip": "Great for painting vivid scenes in writing."
    },
    {
      "term": "Ambiguous",
      "definition": "Open to more than one interpretation.",
      "example": "Her reply was ambiguous, leaving everyone confused.",
      "relevance": "Useful in argumentative writing.",
      "tip": "Use when discussing unclear statements or ideas."
    },
    {
      "term": "Ubiquitous",
      "definition": "Present, appearing, or found everywhere.",
      "example": "Smartphones are ubiquitous in today’s society.",
      "relevance": "Common in academic writing.",
      "tip": "Use to describe something widespread."
    },
    {
      "term": "Eloquent",
      "definition": "Fluent or persuasive in speaking or writing.",
      "example": "Her eloquent speech moved the entire audience.",
      "relevance": "Useful for essays and speaking sections.",
      "tip": "Use when praising strong communication skills."
    },
    {
      "term": "Inevitable",
      "definition": "Certain to happen; unavoidable.",
      "example": "With such bad weather, cancellation was inevitable.",
      "relevance": "Great for cause-effect essays.",
      "tip": "Use to describe unavoidable outcomes."
    },
    {
      "term": "Ephemeral",
      "definition": "Lasting for a very short time.",
      "example": "Fame can be ephemeral in the digital age.",
      "relevance": "Impressive for abstract topics.",
      "tip": "Use to discuss fleeting trends."
    },
    {
      "term": "Meticulous",
      "definition": "Showing great attention to detail.",
      "example": "She kept meticulous records of her experiments.",
      "relevance": "Useful in science and academic essays.",
      "tip": "Use when describing perfectionism or care."
    },
    {
      "term": "Resilient",
      "definition": "Able to recover quickly from difficulties.",
      "example": "Children are often more resilient than adults expect.",
      "relevance": "Great for personal or motivational writing.",
      "tip": "Use in discussions of adversity and strength."
    },
    {
      "term": "Imminent",
      "definition": "About to happen.",
      "example": "A storm is imminent, so take shelter.",
      "relevance": "Useful in weather, politics, or risk topics.",
      "tip": "Use to create urgency."
    },
    {
      "term": "Scrutinize",
      "definition": "To examine very closely.",
      "example": "The committee will scrutinize the report before approval.",
      "relevance": "Useful in academic and legal contexts.",
      "tip": "Use when describing careful inspection."
    },
    {
      "term": "Pragmatic",
      "definition": "Dealing with things sensibly and realistically.",
      "example": "We need a pragmatic approach to solve this issue.",
      "relevance": "Useful in problem-solving contexts.",
      "tip": "Use to contrast idealistic viewpoints."
    },
    {
      "term": "Juxtapose",
      "definition": "To place side by side for comparison.",
      "example": "The author juxtaposes war and peace throughout the novel.",
      "relevance": "Common in literary analysis.",
      "tip": "Use when comparing ideas or imagery."
    },
    {
      "term": "Obsolete",
      "definition": "No longer in use.",
      "example": "CDs have become obsolete with the rise of streaming.",
      "relevance": "Useful in technology topics.",
      "tip": "Use to describe outdated items."
    },
    {
      "term": "Alleviate",
      "definition": "To relieve or reduce pain or burden.",
      "example": "New policies aim to alleviate poverty.",
      "relevance": "Useful in health or policy writing.",
      "tip": "Use when discussing solutions."
    },
    {
      "term": "Conundrum",
      "definition": "A confusing or difficult problem.",
      "example": "Choosing between two jobs is a real conundrum.",
      "relevance": "Good for argument or dilemma essays.",
      "tip": "Use to show complex issues."
    },
    {
      "term": "Aesthetic",
      "definition": "Concerned with beauty or artistic impact.",
      "example": "The building has great aesthetic appeal.",
      "relevance": "Useful in design, culture, and art topics.",
      "tip": "Use to praise visual design."
    },
    {
      "term": "Prolific",
      "definition": "Producing a large amount of something.",
      "example": "Shakespeare was a prolific playwright.",
      "relevance": "Useful in literature or data essays.",
      "tip": "Use to describe quantity and creativity."
    },
    {
      "term": "Tedious",
      "definition": "Too long, slow, or dull; tiresome.",
      "example": "The process of applying was tedious but necessary.",
      "relevance": "Good for describing challenges.",
      "tip": "Use to describe repetitive tasks."
    },
    {
      "term": "Cohesive",
      "definition": "Well integrated and unified.",
      "example": "Her essay was well-organized and cohesive.",
      "relevance": "Useful for writing evaluation.",
      "tip": "Use when judging structure or flow."
    },
    {
      "term": "Exacerbate",
      "definition": "To make a problem worse.",
      "example": "Pollution exacerbates climate change.",
      "relevance": "Strong for cause-effect essays.",
      "tip": "Use for negative escalation."
    },
    {
      "term": "Diligent",
      "definition": "Hard-working and careful.",
      "example": "He is diligent in his studies.",
      "relevance": "Common in work or education topics.",
      "tip": "Use to describe a good habit."
    },
    {
      "term": "Vulnerable",
      "definition": "Easily affected or hurt.",
      "example": "Elderly people are vulnerable to illness.",
      "relevance": "Useful in health and society topics.",
      "tip": "Use when discussing risks or protection."
    },
    {
      "term": "Benevolent",
      "definition": "Kind and generous.",
      "example": "The organization is known for its benevolent work.",
      "relevance": "Useful in describing character.",
      "tip": "Use when discussing philanthropy."
    },
    {
      "term": "Intricate",
      "definition": "Very detailed and complicated.",
      "example": "The design of the sculpture is intricate.",
      "relevance": "Useful in art and science essays.",
      "tip": "Use to describe complexity."
    },
    {
      "term": "Hypothetical",
      "definition": "Based on a theory or assumption.",
      "example": "This is a hypothetical situation, not real.",
      "relevance": "Common in examples and reasoning.",
      "tip": "Use to introduce imagined cases."
    },
    {
      "term": "Ameliorate",
      "definition": "To improve or make better.",
      "example": "Efforts were made to ameliorate living conditions.",
      "relevance": "Good for discussing solutions.",
      "tip": "Use in formal improvement contexts."
    },
    {
      "term": "Plausible",
      "definition": "Seeming reasonable or probable.",
      "example": "Her excuse was plausible, though not certain.",
      "relevance": "Useful in reasoning or argument.",
      "tip": "Use to describe believable claims."
    },
    {
      "term": "Indigenous",
      "definition": "Originating or occurring naturally in a region.",
      "example": "These plants are indigenous to South America.",
      "relevance": "Useful in environmental and cultural topics.",
      "tip": "Use when discussing native populations or ecosystems."
    },
    {
      "term": "Ostentatious",
      "definition": "Showy and intended to impress.",
      "example": "His ostentatious lifestyle drew criticism.",
      "relevance": "Great for tone or character description.",
      "tip": "Use when describing excessive behavior."
    },
    {
      "term": "Candid",
      "definition": "Truthful and straightforward.",
      "example": "He gave a candid account of the incident.",
      "relevance": "Useful in interviews and honesty contexts.",
      "tip": "Use when describing openness or sincerity."
    }
  


]

@app.get("/daily-grammar-words")
def get_random_words():
    return {"words": random.sample(word_pool, 3)}
