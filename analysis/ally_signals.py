from typing import Optional


def get_hero_ally_winrates(conn, player_uid: int, hero_played: str) -> list[dict]:
    """Win rate on hero_played broken down by each ally hero present."""
    sql = """
        SELECT
            ally,
            COUNT(*) AS games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
        FROM user_matches,
             UNNEST(ally_heroes) AS ally
        WHERE player_uid = %s
          AND hero_played = %s
          AND ally_heroes IS NOT NULL
        GROUP BY ally
        HAVING COUNT(*) >= 3
        ORDER BY win_rate DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (player_uid, hero_played))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_top_synergies_for_hero(conn, player_uid: int, hero_played: str, min_games: int = 3) -> list[dict]:
    """Best ally heroes to have when playing hero_played, ranked by win rate delta vs baseline."""
    baseline_sql = """
        SELECT ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4)
        FROM user_matches
        WHERE player_uid = %s AND hero_played = %s
    """
    with conn.cursor() as cur:
        cur.execute(baseline_sql, (player_uid, hero_played))
        row = cur.fetchone()
    baseline_wr = float(row[0]) if row and row[0] else None

    ally_rates = get_hero_ally_winrates(conn, player_uid, hero_played)

    results = []
    for entry in ally_rates:
        if int(entry["games"]) < min_games:
            continue
        wr = float(entry["win_rate"])
        delta = round(wr - baseline_wr, 4) if baseline_wr is not None else None
        results.append({
            "ally": entry["ally"],
            "games": int(entry["games"]),
            "wins": int(entry["wins"]),
            "win_rate": wr,
            "baseline_wr": baseline_wr,
            "delta": delta,
        })

    return sorted(results, key=lambda x: x["win_rate"], reverse=True)


def get_all_hero_pair_winrates(conn, player_uid: int, min_games: int = 3) -> list[dict]:
    """Every (hero_played, ally) pair the player has enough data on, ranked by win rate."""
    sql = """
        SELECT
            hero_played,
            ally,
            COUNT(*) AS games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
        FROM user_matches,
             UNNEST(ally_heroes) AS ally
        WHERE player_uid = %s
          AND ally_heroes IS NOT NULL
        GROUP BY hero_played, ally
        HAVING COUNT(*) >= %s
        ORDER BY win_rate DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (player_uid, min_games))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_best_heroes_on_map(conn, player_uid: int, map_name: str, side: Optional[str] = None, min_games: int = 3) -> list[dict]:
    """Personal win rates per hero on a specific map, optionally filtered by side."""
    if side and side != "unknown":
        sql = """
            SELECT
                hero_played,
                COUNT(*) AS games,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
                ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
            FROM user_matches
            WHERE player_uid = %s AND map_name = %s AND side = %s
            GROUP BY hero_played
            HAVING COUNT(*) >= %s
            ORDER BY win_rate DESC
        """
        params = (player_uid, map_name, side, min_games)
    else:
        sql = """
            SELECT
                hero_played,
                COUNT(*) AS games,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
                ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
            FROM user_matches
            WHERE player_uid = %s AND map_name = %s
            GROUP BY hero_played
            HAVING COUNT(*) >= %s
            ORDER BY win_rate DESC
        """
        params = (player_uid, map_name, min_games)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_synergy_opportunities(conn, player_uid: int, current_hero: str, ally_heroes: list[str]) -> list[dict]:
    """Given current allies in lobby, find historical synergies that apply right now."""
    all_synergies = get_top_synergies_for_hero(conn, player_uid, current_hero)
    active = [s for s in all_synergies if s["ally"] in ally_heroes and s["delta"] and s["delta"] > 0]
    return active
