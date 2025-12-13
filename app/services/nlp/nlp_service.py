import traceback
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, UploadFile
import google.generativeai as genai
import os
from starlette.concurrency import run_in_threadpool
import json
import re
from .prompt_obj_detect import build_prompt_obj_detect
from app.services.semantic.semantic import TaskClassifier, TaskPrediction
from ..quota.quota_service import get_account_quota, consume_quota
from ..stt.stt_service import transcribe_audio
from .skills_loader import load_skills_text
from app.repositories.robot_model_repository import get_robot_prompt_by_id
from app.services.nlp.prompt import PROMPT_TEMPLATE
import tiktoken
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from ...repositories.account_quota_repository import get_account_from_serial
from .vector_context_service import get_conversation_context_service
from ...repositories.esp32_repository import get_esp

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
        print(f"Detected language: {lang} for text: {text}")
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


def format_task_predictions(predictions: List[TaskPrediction]) -> str:
    """
    Format task predictions into a readable string for the prompt

    Args:
        predictions: List of TaskPrediction objects

    Returns:
        Formatted string describing each prediction
    """
    if not predictions:
        return "No task predictions available. Please use 'talk' intent as fallback."
    
    lines = []
    for i, pred in enumerate(predictions, 1):
        confidence = (1.0 - pred.distance) * 100
        
        # Extract key metadata
        task_type = pred.task_type
        description = pred.metadata.get('description', 'No description')
        response_template = pred.metadata.get('response_template', {})
        
        lines.append(f"{i}. Task: {task_type} (confidence: {confidence:.1f}%)")
        lines.append(f"   Description: {description}")
        lines.append(f"   Response template: {response_template}")
        lines.append("")
    
    return "\n".join(lines)


def format_esp32_text(esp32_dict: Optional[Dict[str, Any]]) -> str:
    """
    Chuyển đổi dictionary ESP32 thành text với định dạng:
    ESP ID: {id}
    DEVICE LIST: {metadata}

    Args:
        esp32_dict: Dictionary từ hàm esp32_to_dict()

    Returns:
        Chuỗi text được định dạng
    """
    if esp32_dict is None:
        return "No ESP32 data available"
    
    # Lấy ID
    esp_id = esp32_dict.get("id", "Unknown")
    
    # Lấy metadata và định dạng JSON
    metadata = esp32_dict.get("metadata")
    
    if metadata is None:
        metadata_str = "No metadata"
    else:
        # Định dạng JSON đẹp với indent
        try:
            if isinstance(metadata, str):
                # Nếu metadata là string, cố gắng parse nó
                metadata_parsed = json.loads(metadata)
                metadata_str = json.dumps(metadata_parsed, indent=2, ensure_ascii=False)
            else:
                # Nếu metadata đã là dict/list
                metadata_str = json.dumps(metadata, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # Nếu không thể định dạng JSON, dùng string representation
            metadata_str = str(metadata)
    
    # Tạo text với định dạng yêu cầu
    text = f"ESP ID: {esp_id}\n"
    text += f"DEVICE LIST: {metadata_str}"
    
    return text

async def build_prompt(
        input_text: str,
        robot_model_id: str,
        predictions: List[TaskPrediction],
        context_text: str = None,
        device_text: str = ""
) -> str:
    db_prompt = await get_robot_prompt_by_id(robot_model_id)
    skills_text = await load_skills_text(robot_model_id)
    safe_text = input_text.replace('"', '\\"')
    # fallback nếu DB không có prompt
    prompt_template = db_prompt or PROMPT_TEMPLATE
    base = (
        prompt_template
        .replace("$INPUT_TEXT", safe_text)
        .replace("$CONTEXT_BLOCK", context_text)
        .replace("$SKILL_LIST", skills_text)
        .replace("$DEVICE_LIST", device_text)
    )
    
    if context_text:
        # Prepend a short labeled conversation history block so the LLM has
        # previous turns for context continuity.
        context_block = f"Conversation history:\n{context_text}\n\n"
        return context_block + base
    
    return base


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



async def process_text(input_text: str, robot_model_id: str, serial: str = ''):
    """
    Enhanced version with actual Gemini token usage tracking
    """
    print('\n>>>', input_text, '\n')
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
        account_id = await get_account_from_serial(serial)
        quota_or_sub = await get_account_quota(account_id)
        
        if quota_or_sub['type'] == 'Quota' and quota_or_sub['quota'] <= 0:
            if lang == 'vi' or lang is None:
                content = 'Bạn đã sử dụng hết dung lượng miễn phí cho ngày hôm nay. Vui lòng đăng ký gói để sử dụng thêm'
            else:
                content = 'You have used up all your free data for today. Please subscribe to a plan to use more.'
            return {
                'type': 'talk',
                'data': {
                    'text': content
                }
            }
        esp = await get_esp(account_id)
        # Fetch recent conversation context (per-robot) and build prompt including it
        try:
            ctx_service = get_conversation_context_service()
            recent = await ctx_service.get_recent(serial, k=5) if ctx_service else []
            # recent is sorted newest-first; reverse to chronological order
            recent_chron = list(reversed(recent))
            # create a compact context text; include role label for clarity
            context_text = "\n".join(f"{item['meta'].get('role', 'user')}: {item['text']}" for item in recent_chron)
        except Exception:
            context_text = None
        
        prompt = await build_prompt(input_text, robot_model_id, context_text=context_text, predictions=[],
                                    device_text=format_esp32_text(esp))
        print('Prompt:', prompt)
        response = await run_in_threadpool(
            model.generate_content,
            prompt,
        )
        
        text = response.text
        
        if not text:
            return {'type': 'error', 'data': {"error": "Empty response from Gemini"}}
        
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
        if quota_or_sub['type'] == 'Quota':
            await consume_quota(account_id, actual_total_tokens)
        # prompt already built including context; keep it for token usage debug
        try:
            parsed = json.loads(cleaned)
            parsed["_token_usage"] = {
                "actual_input_tokens": actual_input_tokens,
                "actual_output_tokens": actual_output_tokens,
                "actual_total_tokens": actual_total_tokens,
            }
            
            # Persist conversation messages (user input + assistant reply) to vector DB
            try:
                ctx_svc = get_conversation_context_service()
                user_msg = {"text": input_text, "role": "user"}
                # try to extract assistant textual reply if possible
                assistant_text = None
                if isinstance(parsed, dict):
                    data = parsed.get("data")
                    if isinstance(data, dict):
                        assistant_text = data.get("text")
                if not assistant_text:
                    assistant_text = text
                assistant_msg = {"text": assistant_text, "role": "assistant"}
                ctx_svc.upsert_messages(serial, [user_msg, assistant_msg])
            except Exception:
                # don't fail the response if saving context fails
                pass
            
            return parsed
        except Exception:
            traceback.print_exc()
            return {
                "error": f"Gemini returned invalid JSON: {text}",
                "_token_usage": {
                    "actual_input_tokens": actual_input_tokens,
                    "actual_output_tokens": actual_output_tokens,
                    "actual_total_tokens": actual_total_tokens,
                }
            }
    
    except Exception as e:
        traceback.print_exc()
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
