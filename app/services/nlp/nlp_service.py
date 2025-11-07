from fastapi import HTTPException, UploadFile
import google.generativeai as genai
import os
from starlette.concurrency import run_in_threadpool
import json
import re
from .prompt import build_prompt
from .prompt_obj_detect import build_prompt_obj_detect
from ..quota.quota_service import get_account_quota
from ..stt.stt_service import transcribe_audio
from .skills_loader import load_skills_text
from app.repositories.robot_model_repository import get_robot_prompt_by_id
from app.services.nlp.prompt import PROMPT_TEMPLATE
import tiktoken
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from ...repositories.account_quota_repository import get_account_from_serial

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

DetectorFactory.seed = 0  # make detection deterministic

def detect_lang(text: str) -> str:
    """
    Detect language of a text snippet as 'en', 'vi', or 'none'.
    """
    if not text or not text.strip():
        return "none"
    try:
        lang = detect(text)
        if lang in ("en", "vi"):
            return lang
        return "none"
    except LangDetectException:
        return "none"


async def load_skills_text_async(robot_model_id: str) -> str:
    skills_text = await load_skills_text(robot_model_id)
    return skills_text


async def load_robot_prompt(robot_model_id: str) -> str:
    db_prompt = await get_robot_prompt_by_id(robot_model_id)
    return db_prompt or ""


async def build_prompt(input_text: str, robot_model_id: str) -> str:
    db_prompt = await get_robot_prompt_by_id(robot_model_id)
    skills_text = await load_skills_text(robot_model_id)
    safe_text = input_text.replace('"', '\\"')
    
    # fallback nếu DB không có prompt
    prompt_template = db_prompt or PROMPT_TEMPLATE
    
    return (
        prompt_template
        .replace("$INPUT_TEXT", safe_text)
        .replace("$SKILL_LIST", skills_text)
    )


async def process_audio(req: UploadFile, robot_model_id: str) -> dict:
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


import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold


async def process_text(input_text: str, robot_model_id: str, serial: str = '', max_output_tokens: int = 500):
    """
    Enhanced version with actual Gemini token usage tracking
    """
    if model is None:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini model not initialized: {init_error}"
        )
    
    if serial is None or len(serial) == 0:
        raise HTTPException(
            status_code=400,
            detail='Serial is required'
        )
    
    try:
        lang = detect_lang(input_text)
        if lang == "none":
            return {
                'type': 'talk',
                'lang': 'vi',
                'data': {
                    'text': 'Tôi không hiểu yêu cầu của bạn'
                }
            }
        account_id = await get_account_from_serial(serial)
        quota_or_sub = await get_account_quota(account_id)
        if quota_or_sub[1] == 'Quota' and quota_or_sub[0]['quota'] <= 0:
            content = ''
            if lang == 'vi':
                content == ('Bạn đã sử dụng hết dung lượng miễn phí cho ngày hôm nay. Vui lòng đăng ký gói để sử dụng thêm')
            else:
                content == 'You have used up all your free data for today. Please subscribe to a plan to use more.'
            return {
                'type': 'talk',
                'data': {
                    'text': content
                }
            }
        prompt = await build_prompt(input_text, robot_model_id)
        
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
        )
        response = await run_in_threadpool(
            model.generate_content,
            prompt,
            generation_config=generation_config
        )
        
        text = response.text
        
        if not text:
            return {'type': 'error', 'data': {"error": "Empty response from Gemini"}}
        
        # ACTUAL TOKEN USAGE FROM GEMINI API
        actual_input_tokens = 0
        actual_output_tokens = 0
        actual_total_tokens = 0
        
        if hasattr(response, 'usage_metadata'):
            # This is the ACTUAL token count from Gemini's processing
            actual_input_tokens = response.usage_metadata.prompt_token_count
            actual_output_tokens = response.usage_metadata.candidates_token_count
            actual_total_tokens = response.usage_metadata.total_token_count
        else:
            # Fallback: estimate with tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            actual_input_tokens = len(encoding.encode(prompt))
            actual_output_tokens = len(encoding.encode(text))
            actual_total_tokens = actual_input_tokens + actual_output_tokens
        
        # cleanup JSON response
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        
        try:
            parsed = json.loads(cleaned)
            parsed["_token_usage"] = {
                "actual_input_tokens": actual_input_tokens,
                "actual_output_tokens": actual_output_tokens,
                "actual_total_tokens": actual_total_tokens,
                "max_output_tokens": max_output_tokens,
                "token_limit_respected": actual_output_tokens <= max_output_tokens,
                "actual_prompt": prompt
            }
            return parsed
        except Exception:
            return {
                "error": f"Gemini returned invalid JSON: {text}",
                "_token_usage": {
                    "actual_input_tokens": actual_input_tokens,
                    "actual_output_tokens": actual_output_tokens,
                    "actual_total_tokens": actual_total_tokens,
                    "max_output_tokens": max_output_tokens,
                    "token_limit_respected": actual_output_tokens <= max_output_tokens
                }
            }
    
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
