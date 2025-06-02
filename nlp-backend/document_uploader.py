from fastapi import UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from io import BytesIO
from docx import Document
from utils import correct_with_groq

async def upload_document(file: UploadFile = File(...)):
    content = await file.read()

    try:
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

        raise HTTPException(status_code=400, detail="Unsupported file format. Upload a .docx or .txt file.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
