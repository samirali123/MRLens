from db.queries import get_enemy_weaknesses as _db_get_weaknesses


def get_enemy_weaknesses(conn, enemy_usernames: list[str]) -> dict:
    rows = _db_get_weaknesses(conn, enemy_usernames)
    result = {}
    for row in rows:
        username = row["player_username"]
        if username not in result:
            result[username] = {"worst_heroes": [], "best_heroes": []}
        entry = {
            "hero": row["hero_name"],
            "games": row["games_played"],
            "win_rate": float(row["win_rate"] or 0),
        }
        if float(row["win_rate"] or 0) < 0.45:
            result[username]["worst_heroes"].append(entry)
        elif float(row["win_rate"] or 0) > 0.55:
            result[username]["best_heroes"].append(entry)
    return result


def aggregate_enemy_vulnerabilities(weakness_map: dict) -> dict:
    hero_exploit_count: dict[str, int] = {}
    for _player, data in weakness_map.items():
        for entry in data["worst_heroes"]:
            hero = entry["hero"]
            hero_exploit_count[hero] = hero_exploit_count.get(hero, 0) + 1
    return dict(sorted(hero_exploit_count.items(), key=lambda x: x[1], reverse=True))
