import ollama
from db.queries import log_recommendation

OLLAMA_MODEL = "llama3.1:8b"


def get_recommendation(prompt: str, conn=None, log_meta: dict = None) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    response_text = response.message.content

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
