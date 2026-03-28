"""
Utility functions for interacting with OpenAI's API.
"""

import openai
from .config import OPENAI_API_KEY, OPENAI_MODEL

openai.api_key = OPENAI_API_KEY


async def ask_openai(prompt: str, system_prompt: str | None = None) -> str:
    """Send a prompt to the OpenAI Chat API and return the response."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    try:
        response = await openai.ChatCompletion.acreate(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.6,
        )
    except Exception:
        return "I'm sorry, I couldn't generate a response right now."
    return response["choices"][0]["message"]["content"].strip()


async def summarize_text(text: str) -> str:
    """Summarize a block of text via OpenAI Chat API."""
    summary_prompt = f"Summarize the following text:\n\n{text}"
    return await ask_openai(summary_prompt, system_prompt="You are a helpful assistant that summarizes user text.")
