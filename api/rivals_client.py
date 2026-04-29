import asyncio
import httpx
from config.settings import RIVALS_API_BASE_URL, RIVALS_API_BASE_URL_V2, get_api_headers, RATE_LIMIT_RETRIES, RATE_LIMIT_BACKOFF_BASE


async def _get(client: httpx.AsyncClient, url: str, params: dict = None) -> dict:
    for attempt in range(RATE_LIMIT_RETRIES):
        try:
            resp = await client.get(url, params=params, headers=get_api_headers(), timeout=10.0)
            if resp.status_code == 429:
                wait = RATE_LIMIT_BACKOFF_BASE ** attempt
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt == RATE_LIMIT_RETRIES - 1:
                raise
            await asyncio.sleep(RATE_LIMIT_BACKOFF_BASE ** attempt)
    return {}


async def get_match_history(username: str, limit: int = 50, season: str = None, game_mode: int = None) -> list[dict]:
    url = f"{RIVALS_API_BASE_URL_V2}/player/{username}/match-history"
    params = {"limit": limit}
    if season:
        params["season"] = season
    if game_mode is not None:
        params["game_mode"] = game_mode
    async with httpx.AsyncClient() as client:
        data = await _get(client, url, params)
    return data.get("matches", data if isinstance(data, list) else [])


async def get_match_detail(match_uid: str) -> dict:
    url = f"{RIVALS_API_BASE_URL}/match/{match_uid}"
    async with httpx.AsyncClient() as client:
        return await _get(client, url)


async def get_match_details_batch(match_uids: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        tasks = [_get(client, f"{RIVALS_API_BASE_URL}/match/{uid}") for uid in match_uids]
        return await asyncio.gather(*tasks, return_exceptions=True)


async def get_player_stats(uid: int, season: str = None) -> dict:
    url = f"{RIVALS_API_BASE_URL_V2}/player/{uid}"
    params = {}
    if season:
        params["season"] = season
    async with httpx.AsyncClient() as client:
        return await _get(client, url, params)


async def get_hero_global_stats(hero_name: str) -> dict:
    url = f"{RIVALS_API_BASE_URL}/heroes/hero/{hero_name}/stats"
    async with httpx.AsyncClient() as client:
        data = await _get(client, url)
    matches = data.get("matches", 0)
    wins = data.get("wins", 0)
    data["win_rate"] = round(wins / matches, 4) if matches > 0 else 0.0
    return data


async def get_hero_details(hero_name: str) -> dict:
    url = f"{RIVALS_API_BASE_URL}/heroes/hero/{hero_name}"
    async with httpx.AsyncClient() as client:
        return await _get(client, url)


async def get_map_list() -> dict:
    url = f"{RIVALS_API_BASE_URL}/maps"
    async with httpx.AsyncClient() as client:
        data = await _get(client, url)
    if isinstance(data, list):
        return {item["map_id"]: item["map_name"] for item in data if "map_id" in item}
    return data


def _get_user_camp(players: list[dict], user_uid: int) -> int | None:
    for p in players:
        if p.get("player_uid") == user_uid or p.get("uid") == user_uid:
            return p.get("camp")
    return None


def _primary_hero(player: dict) -> str:
    """Return the hero the player spent the most time on."""
    heroes = player.get("player_heroes", [])
    if not heroes:
        return player.get("hero_name", "")
    best = max(heroes, key=lambda h: h.get("play_time", h.get("time_played", 0)), default=heroes[0])
    return best.get("hero_name", best.get("name", ""))


def get_allies_from_match(match_detail: dict, user_uid: int) -> list[dict]:
    """Return teammates (same camp, excluding the user)."""
    players = match_detail.get("match_players", match_detail.get("players", []))
    user_camp = _get_user_camp(players, user_uid)
    if user_camp is None:
        return []
    return [
        {
            "uid": p.get("player_uid", p.get("uid")),
            "nick_name": p.get("nick_name", p.get("username", "")),
            "hero": _primary_hero(p),
        }
        for p in players
        if p.get("camp") == user_camp
        and p.get("player_uid", p.get("uid")) != user_uid
    ]


def get_enemies_from_match(match_detail: dict, user_uid: int) -> list[dict]:
    players = match_detail.get("match_players", match_detail.get("players", []))
    user_camp = _get_user_camp(players, user_uid)
    if user_camp is None:
        return []
    return [
        {
            "uid": p.get("player_uid", p.get("uid")),
            "nick_name": p.get("nick_name", p.get("username", "")),
            "heroes_played": p.get("player_heroes", []),
        }
        for p in players
        if p.get("camp") != user_camp
    ]
