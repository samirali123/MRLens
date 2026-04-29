"""
Inserts realistic fake match data for UID 1554228221 so Phase 1 can be tested
without a live API ingest. Run once: python seed_test_data.py
"""
import random
from datetime import datetime, timedelta
from db.connection import init_pool, get_conn, release_conn
from db.queries import upsert_user_match

UID = 1554228221
USERNAME = "SamirAli"

HEROES = ["Star-Lord", "Black Panther", "Magneto", "Storm", "Venom",
          "Spider-Man", "Wolverine", "Luna Snow", "Thor", "Hawkeye"]

ALLIES_POOL = ["Magneto", "Venom", "Thor", "Luna Snow", "Loki",
               "Captain America", "Iron Man", "Mantis", "Groot", "Hawkeye",
               "Storm", "Spider-Man", "Doctor Strange", "Scarlet Witch", "Hela"]

MAPS = ["Tokyo 2099", "Yggdrasil", "Symbiotic Surface", "Midtown",
        "Hydra Charteris Base", "Empire of Eternal Night"]

SIDES = ["attack", "defense"]

# Weighted win rates per hero so the data tells a story
HERO_WIN_BIAS = {
    "Star-Lord":    0.70,
    "Black Panther": 0.62,
    "Magneto":      0.45,
    "Storm":        0.55,
    "Venom":        0.40,
    "Spider-Man":   0.60,
    "Wolverine":    0.50,
    "Luna Snow":    0.65,
    "Thor":         0.48,
    "Hawkeye":      0.35,
}

# Star-Lord wins more with Magneto — the key synergy to showcase
SYNERGY_BOOST = {
    ("Star-Lord", "Magneto"):      0.25,
    ("Black-Panther", "Venom"):    0.20,
    ("Storm", "Thor"):             0.15,
    ("Luna Snow", "Spider-Man"):   0.15,
}

# Star-Lord wins more on Tokyo 2099
MAP_BIAS = {
    ("Star-Lord", "Tokyo 2099"):       0.15,
    ("Black Panther", "Symbiotic Surface"): 0.20,
    ("Magneto", "Yggdrasil"):          0.10,
}


def roll_win(hero: str, allies: list[str], map_name: str) -> str:
    base = HERO_WIN_BIAS.get(hero, 0.50)
    for ally in allies:
        base += SYNERGY_BOOST.get((hero, ally), 0)
    base += MAP_BIAS.get((hero, map_name), 0)
    base = min(base, 0.95)
    return "win" if random.random() < base else "loss"


def random_allies(exclude_hero: str) -> list[str]:
    pool = [a for a in ALLIES_POOL if a != exclude_hero]
    return random.sample(pool, 5)


def seed(conn, n: int = 120):
    now = datetime.utcnow()
    inserted = 0
    for i in range(n):
        hero = random.choice(HEROES)
        allies = random_allies(hero)
        map_name = random.choice(MAPS)
        side = random.choice(SIDES)
        result = roll_win(hero, allies, map_name)
        played_at = now - timedelta(hours=i * 2)

        upsert_user_match(conn, {
            "match_uid": f"test-match-{i:04d}",
            "player_username": USERNAME,
            "player_uid": UID,
            "hero_played": hero,
            "map_id": None,
            "map_name": map_name,
            "side": side,
            "result": result,
            "ally_heroes": allies,
            "enemy_comp": [],
            "enemy_uids": [],
            "enemy_usernames": [],
            "kills": random.randint(2, 20),
            "deaths": random.randint(1, 12),
            "assists": random.randint(0, 15),
            "season": "2.0",
            "game_mode_id": 1,
            "played_at": played_at.isoformat(),
        })
        inserted += 1

    print(f"Seeded {inserted} matches for UID {UID} ({USERNAME})")


if __name__ == "__main__":
    init_pool()
    conn = get_conn()
    try:
        seed(conn)
    finally:
        release_conn(conn)
