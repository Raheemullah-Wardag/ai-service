import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash")

def get_chat_response(messages: list[dict]) -> str:
    history = [
        {
            "role": m["role"],
            "parts": [m["content"]]
        }
        for m in messages[:-1]
    ]
    
    chat = model.start_chat(history=history)
    response = chat.send_message(messages[-1]["content"])
    return response.text

async def stream_chat_response(messages: list[dict]):
    role_map = {"assistant": "model", "user": "user"}
    history = [
    {
        "role": role_map.get(m["role"], m["role"]),
        "parts": [m["content"]]
    }
    for m in messages[:-1]
]
    
    chat = model.start_chat(history=history)
    response = chat.send_message(
        messages[-1]["content"],
        stream=True
    )
    
    for chunk in response:
        if chunk.text:
            yield chunk.text