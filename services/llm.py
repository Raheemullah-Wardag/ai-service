from dotenv import load_dotenv
import os

from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _build_contents(messages: list[dict]) -> list:
    contents = []
    for message in messages:
        role = "user" if message["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=message["content"])]
            )
        )
    return contents

def get_chat_response(messages: list[dict]) -> str:
    contents = _build_contents(messages)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.7),
    )
    return response.text or ""

async def stream_chat_response(messages: list[dict]):
    contents = _build_contents(messages)
    response = client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.7),
    )
    for chunk in response:
        if getattr(chunk, "text", None):
            yield chunk.text