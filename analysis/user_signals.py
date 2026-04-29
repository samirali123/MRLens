from db.queries import get_user_hero_stats, get_user_hero_stats_by_map

COMP_ARCHETYPES = {
    "dive": {"Spider-Man", "Black Panther", "Wolverine", "Iron Fist", "Venom", "Psylocke"},
    "poke": {"Hawkeye", "Black Widow", "Star-Lord", "Storm", "Scarlet Witch", "Hela"},
    "sustain": {"Luna Snow", "Mantis", "Loki", "Adam Warlock", "Jeff the Land Shark", "Invisible Woman"},
    "brawl": {"Thor", "Captain America", "Hulk", "Groot", "Thing", "Magneto"},
}


def get_hero_winrates(conn, username: str) -> dict:
    rows = get_user_hero_stats(conn, username)
    return {
        r["hero_played"]: {
            "games": int(r["games"]),
            "wins": int(r["wins"]),
            "win_rate": float(r["win_rate"]),
        }
        for r in rows
    }


def get_hero_winrates_on_map(conn, username: str, map_name: str) -> dict:
    rows = get_user_hero_stats_by_map(conn, username, map_name)
    return {
        r["hero_played"]: {
            "games": int(r["games"]),
            "wins": int(r["wins"]),
            "win_rate": float(r["win_rate"]),
        }
        for r in rows
    }


def classify_comp(enemy_heroes: list[str]) -> str:
    scores = {archetype: 0 for archetype in COMP_ARCHETYPES}
    for hero in enemy_heroes:
        for archetype, hero_set in COMP_ARCHETYPES.items():
            if hero in hero_set:
                scores[archetype] += 1
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else "mixed"


def get_winrate_vs_archetype(conn, username: str, archetype: str) -> dict:
    archetype_heroes = COMP_ARCHETYPES.get(archetype, set())
    sql = """
        SELECT
            hero_played,
            COUNT(*) AS games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
        FROM user_matches
        WHERE player_username = %s
          AND enemy_comp && %s
        GROUP BY hero_played
        ORDER BY games DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (username, list(archetype_heroes)))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return {
        r[0]: {"games": int(r[1]), "wins": int(r[2]), "win_rate": float(r[3])}
        for r in rows
    }
