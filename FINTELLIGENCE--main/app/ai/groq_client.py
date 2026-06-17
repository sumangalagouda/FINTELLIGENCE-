import os
from groq import Groq

client = None
if os.environ.get("GROQ_API_KEY"):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

def call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    if not os.environ.get("GROQ_API_KEY") or not client:
        return get_mock_response(user_prompt)
    
    response = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", "llama3-70b-8192"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.1
    )
    return response.choices[0].message.content

def get_mock_response(user_prompt: str) -> str:
    return f"[MOCK RESPONSE] This is a placeholder. Add GROQ_API_KEY to .env to get real AI analysis. Query was: {user_prompt[:50]}..."
