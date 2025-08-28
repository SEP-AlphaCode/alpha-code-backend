import csv
import io

from fastapi import HTTPException, UploadFile
import google.generativeai as genai
import os
from starlette.concurrency import run_in_threadpool
import json
import re
from .prompt import build_prompt
from .prompt_dance import build_prompt as build_dance_prompt
from ..stt.stt_service import transcribe_audio

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


async def process_audio(req: UploadFile):
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
    prompt = build_prompt(text_from_stt)

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


async def process_text(input_text: str):
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
    prompt = build_prompt(input_text)

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

def json_to_csv_text(json_data: dict) -> str:
    """Convert actions + expressions JSON to CSV text."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "description", "duration", "type"])

    for item in json_data.get("actions", []):
        writer.writerow([
            item.get("id", ""),
            item.get("description", ""),
            item.get("duration", ""),
            "dance"
        ])

    for item in json_data.get("expressions", []):
        writer.writerow([
            item.get("id", ""),
            item.get("description", ""),
            item.get("duration", ""),
            "expression"
        ])

    return output.getvalue()

async def analyze_dance(audio_file: UploadFile, json_file: UploadFile) -> str:
    """
    Analyze audio + JSON actions and return a dance routine.

    Args:
        audio_file: Path to the audio file (e.g., .wav or .mp3).
        json_file: Path to the JSON file containing actions and expressions.

    Returns:
        The model response as a JSON string (strict JSON array).
    """
    # Load JSON file
    json_bytes = await json_file.read()
    json_data = json.loads(json_bytes.decode("utf-8"))

    # Convert to CSV
    csv_text = json_to_csv_text(json_data)
    full_prompt = build_dance_prompt() + "\n" + csv_text
    audio_bytes = await audio_file.read()
    # Call Gemini with multimodal input
    response = model.generate_content(
        [
            full_prompt,
            {
                "mime_type": audio_file.content_type or "audio/wav",
                "data": audio_bytes,
            }
        ]
    )
    cleaned = re.sub(r"^```(?:json)?|```$", "", response.text.strip(), flags=re.MULTILINE).strip()
    return cleaned