from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from docx import Document
import httpx
import os
from dotenv import load_dotenv
from services.grammar_checker import analyze_sentence_with_groq

load_dotenv()  # Load your .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins or specify your React app origin here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema for sentence analysis
class SentenceRequest(BaseModel):
    sentence: str

# Response schema for sentence analysis
class SentenceResponse(BaseModel):
    corrected: str
    score: str
    explanation: str

# Request schema for document upload
class DocumentResponse(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}

# ✅ Sentence analysis endpoint
@app.post("/analyze-sentence", response_model=SentenceResponse)
async def analyze_sentence(request: SentenceRequest):
    try:
        result = await analyze_sentence_with_groq(request.sentence)
        print(result)  # Optional: for debugging
        return SentenceResponse(**result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ---------- Groq API Grammar Correction for Sentence Analysis ----------
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

    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            data = response.json()
            print("Groq Response:", data)

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"[Error] Groq API: {data.get('error', {}).get('message', 'Unexpected response')}"
        except httpx.RequestError as e:
            return f"[Request Error] {str(e)}"

# ---------- Document Upload and Correction ----------
# ---------- Document Upload and Correction ----------
@app.post("/upload-document")  # 🔄 changed from /upload-document
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

        return StreamingResponse(output,
                                 media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                 headers={'Content-Disposition': 'attachment; filename="corrected_document.docx"'})

    elif file.filename.endswith(".txt"):
        text = content.decode("utf-8")
        corrected = await correct_with_groq(text)

        output = BytesIO(corrected.encode("utf-8"))
        output.seek(0)

        return StreamingResponse(output,
                                 media_type='text/plain',
                                 headers={'Content-Disposition': 'attachment; filename="corrected_document.txt"'})

    return JSONResponse(content={"error": "Unsupported file format. Upload a .docx or .txt file."}, status_code=400)
