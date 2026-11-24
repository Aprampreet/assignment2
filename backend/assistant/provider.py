import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def explain(template):
    key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL")
    if not key or not model:
        return None
    data = {
        "model": model,
        "messages": [{"role": "system", "content": "Rephrase the supplied Medora navigation instructions in up to two sentences. Add no claims and no medical advice."},
                     {"role": "user", "content": template}],
        "max_completion_tokens": 100,
        "temperature": 0.2,
    }
    req = Request("https://api.groq.com/openai/v1/chat/completions", json.dumps(data).encode(),
                  {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=4) as response:
            result = json.loads(response.read(65536))
        content = result["choices"][0]["message"]["content"]
        return content.strip()[:800] if isinstance(content, str) else None
    except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError):
        return None
