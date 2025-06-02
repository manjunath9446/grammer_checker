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
                corrected_content = data["choices"][0]["message"]["content"].strip()
                
                # Remove unnecessary parts of the response
                # Remove "Here is the corrected text:" and clean up the response.
                corrected_content = corrected_content.replace("Here is the corrected text:", "").strip()
                
                # Optionally remove explanation of errors (you can keep or remove this)
                corrected_sentence = corrected_content.split("\n")[0]  # Only get the first line (corrected sentence)
                
                return corrected_sentence

            else:
                raise Exception("Unexpected response from Groq API")

        except httpx.RequestError as e:
            raise Exception(f"[Request Error] {str(e)}")
