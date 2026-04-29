from typing import Optional


def upsert_user_match(conn, match: dict) -> None:
    sql = """
        INSERT INTO user_matches (
            match_uid, player_username, player_uid, hero_played,
            map_id, map_name, side, result,
            ally_heroes, enemy_comp, enemy_uids, enemy_usernames,
            kills, deaths, assists, season, game_mode_id, played_at
        ) VALUES (
            %(match_uid)s, %(player_username)s, %(player_uid)s, %(hero_played)s,
            %(map_id)s, %(map_name)s, %(side)s, %(result)s,
            %(ally_heroes)s, %(enemy_comp)s, %(enemy_uids)s, %(enemy_usernames)s,
            %(kills)s, %(deaths)s, %(assists)s,
            %(season)s, %(game_mode_id)s, %(played_at)s
        )
        ON CONFLICT (match_uid) DO UPDATE SET
            map_name        = EXCLUDED.map_name,
            side            = EXCLUDED.side,
            ally_heroes     = EXCLUDED.ally_heroes,
            enemy_comp      = EXCLUDED.enemy_comp,
            enemy_uids      = EXCLUDED.enemy_uids,
            enemy_usernames = EXCLUDED.enemy_usernames
    """
    with conn.cursor() as cur:
        cur.execute(sql, match)
    conn.commit()


def upsert_enemy_profile(conn, player_uid: int, player_username: str, hero_data: dict, season: str, is_private: bool = False) -> None:
    sql = """
        INSERT INTO enemy_profiles (
            player_uid, player_username, hero_name, games_played, wins, losses,
            win_rate, season, is_private, last_updated
        ) VALUES (
            %(player_uid)s, %(player_username)s, %(hero_name)s, %(games_played)s,
            %(wins)s, %(losses)s, %(win_rate)s, %(season)s, %(is_private)s, NOW()
        )
        ON CONFLICT (player_uid, hero_name, season) DO UPDATE SET
            player_username = EXCLUDED.player_username,
            games_played    = EXCLUDED.games_played,
            wins            = EXCLUDED.wins,
            losses          = EXCLUDED.losses,
            win_rate        = EXCLUDED.win_rate,
            is_private      = EXCLUDED.is_private,
            last_updated    = NOW()
    """
    row = {
        "player_uid": player_uid,
        "player_username": player_username,
        "hero_name": hero_data["hero_name"],
        "games_played": hero_data.get("games_played", 0),
        "wins": hero_data.get("wins", 0),
        "losses": hero_data.get("losses", 0),
        "win_rate": hero_data.get("win_rate"),
        "season": season,
        "is_private": is_private,
    }
    with conn.cursor() as cur:
        cur.execute(sql, row)
    conn.commit()


def upsert_map_cache(conn, map_id: int, map_name: str) -> None:
    sql = """
        INSERT INTO map_cache (map_id, map_name, cached_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (map_id) DO UPDATE SET map_name = EXCLUDED.map_name, cached_at = NOW()
    """
    with conn.cursor() as cur:
        cur.execute(sql, (map_id, map_name))
    conn.commit()


def get_map_name(conn, map_id: int) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT map_name FROM map_cache WHERE map_id = %s", (map_id,))
        row = cur.fetchone()
    return row[0] if row else None


def get_user_hero_stats(conn, username: str) -> list[dict]:
    sql = """
        SELECT
            hero_played,
            COUNT(*) AS games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
        FROM user_matches
        WHERE player_username = %s
        GROUP BY hero_played
        ORDER BY games DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (username,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_user_hero_stats_by_map(conn, username: str, map_name: str) -> list[dict]:
    sql = """
        SELECT
            hero_played,
            COUNT(*) AS games,
            SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
            ROUND(SUM(CASE WHEN result = 'win' THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS win_rate
        FROM user_matches
        WHERE player_username = %s AND map_name = %s
        GROUP BY hero_played
        ORDER BY games DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (username, map_name))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_enemy_weaknesses(conn, enemy_usernames: list[str]) -> list[dict]:
    sql = """
        SELECT
            player_username,
            hero_name,
            games_played,
            wins,
            losses,
            win_rate
        FROM enemy_profiles
        WHERE player_username = ANY(%s)
          AND games_played >= 5
        ORDER BY player_username, win_rate ASC
    """
    with conn.cursor() as cur:
        cur.execute(sql, (enemy_usernames,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def log_recommendation(conn, log: dict) -> None:
    sql = """
        INSERT INTO recommendation_log (
            player_username, map_name, enemy_uids, enemy_usernames,
            detected_via, llm_prompt, llm_response, recommended_heroes
        ) VALUES (
            %(player_username)s, %(map_name)s, %(enemy_uids)s, %(enemy_usernames)s,
            %(detected_via)s, %(llm_prompt)s, %(llm_response)s, %(recommended_heroes)s
        )
    """
    with conn.cursor() as cur:
        cur.execute(sql, log)
    conn.commit()
