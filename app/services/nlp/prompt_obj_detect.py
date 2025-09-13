"""Prompt template and builder for Gemini NLP intent classification.

Keeping the large language model prompt in a dedicated module makes it easier
to maintain, reuse, test, and potentially localize.
"""

from pathlib import Path
from textwrap import dedent
from typing import Final

PROMPT_TEMPLATE: Final[str] = dedent(
    """
    You are Alpha Mini, an educational robot. You are asked to identify what this object is
    Analyze the input label and return the result **only as JSON** (no explanation, no extra text).

    Input: "$INPUT_TEXT"
    Language: "$LANGUAGE"
    
    - The input is the result of a different object detection process, always in English
    - Your job is to write a response announcing what this label is in the supplied language. en = English, vi = Vietnamese
    For example:
    Input: Fish
    Language: en
    Result: I see a fish
    
    Input: Fish
    Language: vi
    Result: Tôi thấy một con cá
    
    Language Rules:
    - If the language is Vietnamese, respond in Vietnamese. Set the "lang" field in the JSON as "vi"
    - If the language is English, respond in English. Set the "lang" field in the JSON as "en"
    - Do not speak in any other languages
    
    Always return this exact format:
    {
         "type": "object_detect_result",
         "lang": ...,
         "data": {
           "text": I see a ... (English) or Tôi thấy ... (Vietnamese)
         }
    }
   - Change the output to make the response text grammatically correct
   
    """
).strip()


def build_prompt_obj_detect(input_text: str, lang: str) -> str:
    """Return the full prompt with the user input embedded.

    Escapes double quotes in the input to keep JSON inside prompt consistent.
    """
    safe_text = input_text.replace('"', '\\"')
    return PROMPT_TEMPLATE.replace("$INPUT_TEXT", safe_text).replace("$LANGUAGE", lang)


__all__ = ["build_prompt_obj_detect", "PROMPT_TEMPLATE"]