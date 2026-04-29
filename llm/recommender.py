import anthropic
from config.settings import ANTHROPIC_API_KEY
from db.queries import log_recommendation

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def get_recommendation(prompt: str, conn=None, log_meta: dict = None) -> str:
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = message.content[0].text

    if conn and log_meta:
        recommended_heroes = _parse_hero_names(response_text)
        log_recommendation(conn, {
            **log_meta,
            "llm_prompt": prompt,
            "llm_response": response_text,
            "recommended_heroes": recommended_heroes,
        })

    return response_text


def _parse_hero_names(response: str) -> list[str]:
    heroes = []
    for line in response.strip().splitlines():
        line = line.strip()
        if line and line[0].isdigit() and ". " in line:
            after_num = line.split(". ", 1)[1]
            hero = after_num.split(" — ")[0].strip()
            heroes.append(hero)
    return heroes
