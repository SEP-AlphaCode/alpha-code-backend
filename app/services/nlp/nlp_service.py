from fastapi import HTTPException, UploadFile
import google.generativeai as genai
import os
from starlette.concurrency import run_in_threadpool
import json
import re
from .prompt import build_prompt
from .prompt_obj_detect import build_prompt_obj_detect
from ..stt.stt_service import transcribe_audio
from .skills_loader import load_skills_text
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

async def load_skills_text_async(robot_model_id: str) -> str:
    skills_text = await load_skills_text(robot_model_id)
    return skills_text

async def process_audio(req: UploadFile, robot_model_id: str ) -> dict:
    try:
        text_from_stt = await transcribe_audio(req)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"{e}"
        )
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
    prompt = await build_prompt(text_from_stt, robot_model_id)

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


async def process_text(input_text: str, robot_model_id: str):
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
    prompt = await build_prompt(input_text, robot_model_id)
    
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
            return {"error": "Empty response from Gemini"}
        
        # cleanup nếu Gemini vẫn trả về với code fences
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        
        # đảm bảo parse được JSON
        try:
            parsed = json.loads(cleaned)
            return parsed
        except Exception:
            return {"error": f"Gemini returned invalid JSON: {text}"}
    
    except Exception as e:
        return {"error": f"Gemini generation failed: {e}"}


async def process_obj_detect(label: str, lang: str):
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
    prompt = build_prompt_obj_detect(label, lang)
    
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
            return {"error": "Empty response from Gemini"}
        
        # cleanup nếu Gemini vẫn trả về với code fences
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        
        # đảm bảo parse được JSON
        try:
            parsed = json.loads(cleaned)
            return parsed
        except Exception:
            return {"error": f"Gemini returned invalid JSON: {text}"}
    
    except Exception as e:
        return {"error": f"Gemini generation failed: {e}"}