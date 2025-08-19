from fastapi import FastAPI, HTTPException
import google.generativeai as genai
import os
from starlette.concurrency import run_in_threadpool
from app.models.nlp import NLPRequest
import json
import re

# =========================
# Config Gemini
# =========================
key = os.getenv("GEMINI_API_KEY")
gemini_model = os.getenv("GEMINI_MODEL")

if key and gemini_model:
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(gemini_model)
        init_error = None
    except Exception as e:
        model = None
        init_error = str(e)
else:
    model = None
    init_error = "Missing GEMINI_API_KEY or GEMINI_MODEL environment variables"

# =========================
# FastAPI init
# =========================
app = FastAPI()


@app.post("/nlp")
async def process_text(req: NLPRequest):
    """
    Nhận text từ client, gửi qua Gemini để phân tích intent
    và trả về JSON chuẩn theo rule.
    """
    if model is None:
        raise HTTPException(
            status_code=500, 
            detail=f"Gemini model not initialized: {init_error}"
        )

    prompt = f"""
You are Alpha Mini, an educational robot. 
Analyze the input text and return the result **only as JSON** (no explanation, no extra text).

Input: "{req.text}"

Rules:
1. Detect the intent of the sentence. Allowed values for "type" are:
   - "greeting" (hello, hi, good morning…)
   - "qr-code" (when user asks about QR code or scanning)
   - "study" (learning, vocabulary, teaching…)
   - "dance" (dance, move, but not with music)
   - "dance-with-music" (dance with rhythm, music, or song)
   - "unknown" (if it does not match any intent above)

2. Special rule for "qr-code":
   Always return this exact format:
   {{
     "type": "qr-code",
     "data": {{
       "text": "Please place the QR card under my feet in my view. Now I will bend down to scan it."
     }}
   }}

3. For other intents:
   - Always respond in English, friendly and suitable for students.
   - Use this strict JSON format:
   {{
     "type": "<one_of: greeting | study | dance | dance-with-music | unknown>",
     "data": {{
       "text": "<your English response here>"
     }}
   }}

Important:
- Output must be strict JSON.
- Do not use markdown or code fences (```json ... ```).
"""

    try:
        # gọi Gemini ở threadpool (async safe)
        response = await run_in_threadpool(model.generate_content, prompt)

        text = getattr(response, "text", None)

        # fallback nếu Gemini trả về trong candidates
        if not text and hasattr(response, "candidates"):
            try:
                text = "".join(
                    part.text
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "text")
                )
            except Exception:
                text = str(response)

        if not text:
            raise HTTPException(status_code=500, detail="Empty response from Gemini")

        # cleanup nếu Gemini vẫn trả về với code fences
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

        # đảm bảo parse được JSON
        try:
            parsed = json.loads(cleaned)
        except Exception:
            raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {text}")

        return parsed

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini generation failed: {e}")