from dotenv import load_dotenv
import os

from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _build_contents(messages: list[dict]) -> list[dict] | str:
    if not messages:
        return ""

    if len(messages) == 1:
        return messages[-1]["content"]

    contents = []
    for message in messages[:-1]:
        role = "user" if message["role"] == "user" else "model"
        contents.append({"role": role, "parts": [message["content"]]})

    return contents + [{"role": "user", "parts": [messages[-1]["content"]]}]


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