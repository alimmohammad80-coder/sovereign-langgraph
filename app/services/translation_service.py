import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TRANSLATION_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4.1-mini")

def translate_to_english(text: str):
    if not text or not text.strip():
        return ""

    response = client.responses.create(
        model=TRANSLATION_MODEL,
        input=f"""
Translate the following text into clear professional English.
Return only the translation, no explanation.

Text:
{text}
"""
    )

    return response.output_text.strip()
