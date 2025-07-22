import os
import httpx
import json

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-3.5-turbo"

async def ask_llm_stream(prompt: str):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", OPENAI_URL, headers=headers, json=payload, timeout=None) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        if line.startswith("data: "):
                            data = json.loads(line[len("data: "):])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content")
                            if token:
                                yield token
                    except Exception:
                        continue