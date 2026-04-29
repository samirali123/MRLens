from typing import Optional


def get_rank_winrates(conn, rank_tier: str, game_mode: str = "competitive") -> dict:
    sql = """
        SELECT hero_name, win_rate, pick_rate
        FROM meta_win_rates_rank
        WHERE rank_tier = %s AND game_mode = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (rank_tier, game_mode))
        return {row[0]: {"win_rate": float(row[1] or 0), "pick_rate": float(row[2] or 0)} for row in cur.fetchall()}


def get_map_winrates(conn, map_name: str, rank_tier: str = "All") -> dict:
    sql = """
        SELECT hero_name, win_rate
        FROM meta_win_rates_map
        WHERE map_name = %s AND rank_tier = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (map_name, rank_tier))
        return {row[0]: float(row[1] or 0) for row in cur.fetchall()}


def compute_personal_vs_community_delta(personal: dict, community: dict) -> dict:
    result = {}
    for hero, stats in personal.items():
        personal_wr = stats["win_rate"]
        community_wr = community.get(hero, {}).get("win_rate") if isinstance(community.get(hero), dict) else community.get(hero)
        if community_wr is not None:
            result[hero] = {
                "personal": personal_wr,
                "community": community_wr,
                "delta": round(personal_wr - community_wr, 4),
                "games": stats["games"],
            }
        else:
            result[hero] = {
                "personal": personal_wr,
                "community": None,
                "delta": None,
                "games": stats["games"],
            }
    return result
