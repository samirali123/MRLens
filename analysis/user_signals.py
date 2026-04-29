from db.queries import get_user_hero_stats, get_user_hero_stats_by_map

# Canonical hero name → aliases (for OCR fuzzy matching and user input normalisation)
HERO_ALIASES = {
    "Scarlet Witch": ["Wanda", "Scarlet Witch"],
    "Winter Soldier": ["Bucky", "Winter Soldier"],
    "Phoenix":        ["Jean", "Jean Grey", "Phoenix"],
    "TankPool":       ["Deadpool Tank", "TankPool"],
    "DpsPool":        ["Deadpool DPS", "DpsPool"],
    "SupportPool":    ["Deadpool Support", "SupportPool"],
}
ALIAS_TO_CANONICAL = {
    alias.lower(): canonical
    for canonical, aliases in HERO_ALIASES.items()
    for alias in aliases
}

VANGUARDS = {
    "Hulk", "Doctor Strange", "Groot", "Magneto", "Peni Parker",
    "The Thing", "Venom", "Captain America", "Thor", "Emma Frost",
    "Angela", "Rogue", "TankPool",
}

DUELISTS = {
    "Storm", "Human Torch", "Hawkeye", "Hela", "Black Panther", "Magik",
    "Moon Knight", "Black Widow", "Iron Man", "Squirrel Girl", "Spider-Man",
    "Scarlet Witch", "Winter Soldier", "Star-Lord", "Namor", "Psylocke",
    "Wolverine", "Iron Fist", "Phoenix", "The Punisher", "Black Cat",
    "Mister Fantastic", "Blade", "Daredevil", "DpsPool", "Elsa Bloodstone",
}

STRATEGISTS = {
    "Loki", "Mantis", "Rocket Raccoon", "Cloak & Dagger", "Luna Snow",
    "Adam Warlock", "Jeff the Land Shark", "Invisible Woman", "Ultron",
    "Gambit", "White Fox", "SupportPool",
}

DEADPOOL_VARIANTS = {"TankPool", "DpsPool", "SupportPool"}

ALL_HEROES = VANGUARDS | DUELISTS | STRATEGISTS

COMP_ARCHETYPES = {
    "dive":    {"Spider-Man", "Black Panther", "Wolverine", "Iron Fist",
                "Venom", "Psylocke", "Daredevil", "Black Cat"},
    "poke":    {"Hawkeye", "Black Widow", "Star-Lord", "Storm",
                "Scarlet Witch", "Hela", "Elsa Bloodstone"},
    "sustain": {"Luna Snow", "Mantis", "Loki", "Adam Warlock",
                "Jeff the Land Shark", "Invisible Woman", "Ultron",
                "Gambit", "White Fox"},
    "brawl":   {"Thor", "Captain America", "Hulk", "Groot",
                "The Thing", "Magneto", "Angela", "Rogue", "Emma Frost"},
}


def resolve_hero_name(name: str) -> str:
    """Normalise alias or misspelling to canonical hero name."""
    return ALIAS_TO_CANONICAL.get(name.lower(), name)


def get_hero_winrates(conn, player_uid: int) -> dict:
    rows = get_user_hero_stats(conn, player_uid)
    return {
        r["hero_played"]: {
            "games": int(r["games"]),
            "wins": int(r["wins"]),
            "win_rate": float(r["win_rate"]),
        }
        for r in rows
    }


def get_hero_winrates_on_map(conn, player_uid: int, map_name: str) -> dict:
    rows = get_user_hero_stats_by_map(conn, player_uid, map_name)
    return {
        r["hero_played"]: {
            "games": int(r["games"]),
            "wins": int(r["wins"]),
            "win_rate": float(r["win_rate"]),
        }
        for r in rows
    }


def classify_comp(heroes: list[str]) -> str:
    resolved = [resolve_hero_name(h) for h in heroes]
    scores = {archetype: 0 for archetype in COMP_ARCHETYPES}
    for hero in resolved:
        for archetype, hero_set in COMP_ARCHETYPES.items():
            if hero in hero_set:
                scores[archetype] += 1
    top_score = max(scores.values())
    if top_score < 2:
        return "mixed"
    return max(scores, key=scores.get)


def get_winrate_vs_archetype(conn, player_uid: int, archetype: str) -> dict:
    archetype_heroes = list(COMP_ARCHETYPES.get(archetype, set()))
    sql = """
        SELECT
            hero_played,
            COUNT(*) AS games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
        FROM user_matches
        WHERE player_uid = %s
          AND enemy_comp && %s
        GROUP BY hero_played
        ORDER BY games DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (player_uid, archetype_heroes))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return {
        r[0]: {"games": int(r[1]), "wins": int(r[2]), "win_rate": float(r[3])}
        for r in rows
    }
