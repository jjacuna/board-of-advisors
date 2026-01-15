import requests
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default advisor configurations
DEFAULT_ADVISORS = {
    "cfo": {
        "key": "cfo",
        "name": "Victoria Sterling",
        "role": "CFO - Chief Financial Officer",
        "model": "google/gemini-2.0-flash-001",
        "system_prompt": """You are Victoria Sterling, CFO of the board.
You analyze everything through a financial lens: ROI, costs, risks, profitability.
Keep responses concise (2-3 paragraphs max).
Always consider: budget impact, financial risks, revenue potential."""
    },
    "cto": {
        "key": "cto",
        "name": "Marcus Chen",
        "role": "CTO - Chief Technology Officer",
        "model": "anthropic/claude-3.5-haiku",
        "system_prompt": """You are Marcus Chen, CTO of the board.
You evaluate technical feasibility, scalability, and implementation.
Keep responses concise (2-3 paragraphs max).
Always consider: technical complexity, timeline, resources, tech debt."""
    },
    "cmo": {
        "key": "cmo",
        "name": "Sophia Rodriguez",
        "role": "CMO - Chief Marketing Officer",
        "model": "meta-llama/llama-3.1-8b-instruct",
        "system_prompt": """You are Sophia Rodriguez, CMO of the board.
You focus on market positioning, customer perception, and growth.
Keep responses concise (2-3 paragraphs max).
Always consider: target audience, brand impact, competitive advantage."""
    },
    "ceo": {
        "key": "ceo",
        "name": "Alexandra Wright",
        "role": "CEO - Chief Executive Officer",
        "model": "openai/gpt-4o-mini",
        "system_prompt": """You are Alexandra Wright, CEO of the board.
You've just received advice from your CFO, CTO, and CMO.
Your job is to:
1. Acknowledge each advisor's key points
2. Weigh the different perspectives
3. Make a clear executive decision

IMPORTANT: Always end your response with exactly 3 action items formatted as:

**Action Items:**
- [First concrete action step]
- [Second concrete action step]
- [Third concrete action step]

Be decisive. Keep your main response to 2-3 paragraphs, then add the action items."""
    }
}


def get_advisors():
    """Get all advisors with database overrides."""
    from database import get_advisor_settings

    db_settings = get_advisor_settings()
    advisors = []

    for key in ["cfo", "cto", "cmo"]:
        if key in db_settings:
            advisors.append(db_settings[key])
        else:
            advisors.append(DEFAULT_ADVISORS[key])

    return advisors


def get_ceo():
    """Get CEO config with database override."""
    from database import get_advisor_settings

    db_settings = get_advisor_settings()

    if "ceo" in db_settings:
        return db_settings["ceo"]
    return DEFAULT_ADVISORS["ceo"]


def get_all_advisor_configs():
    """Get all advisor configs for settings UI."""
    from database import get_advisor_settings

    db_settings = get_advisor_settings()
    configs = {}

    for key in ["cfo", "cto", "cmo", "ceo"]:
        if key in db_settings:
            configs[key] = db_settings[key]
        else:
            configs[key] = DEFAULT_ADVISORS[key]

    return configs


def get_advisor_response(advisor: dict, question: str) -> str:
    """Get response from a single advisor via OpenRouter."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://board-of-advisors.up.railway.app",
        "X-Title": "Board of Directors AI"
    }

    payload = {
        "model": advisor["model"],
        "messages": [
            {"role": "system", "content": advisor["system_prompt"]},
            {"role": "user", "content": question}
        ],
        "max_tokens": 500
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)

    # Check for errors before parsing JSON
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except:
            error_msg = response.text[:500]
        raise ValueError(f"OpenRouter API error ({response.status_code}): {error_msg}")

    data = response.json()
    return data["choices"][0]["message"]["content"]


def get_ceo_decision(advisor_responses: list, original_question: str) -> str:
    """CEO synthesizes all advisor input and makes final decision."""
    ceo = get_ceo()

    advisor_summary = "\n\n".join([
        f"**{resp['name']} ({resp['role']}):**\n{resp['response']}"
        for resp in advisor_responses
    ])

    ceo_prompt = f"""The board was asked: "{original_question}"

Here are the responses from your advisors:

{advisor_summary}

Based on all this input, provide your executive decision."""

    return get_advisor_response(ceo, ceo_prompt)
