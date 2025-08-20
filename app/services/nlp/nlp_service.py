from fastapi import HTTPException
import google.generativeai as genai
import os
from starlette.concurrency import run_in_threadpool
from app.models.nlp import NLPRequest
import json
import re
from .prompt import build_prompt

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

    # Build prompt from external template file for maintainability
    prompt = build_prompt(req.text)

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