import argparse
import asyncio
import time

from config.settings import DATABASE_URL
from db.connection import init_pool, get_conn, release_conn
from db.queries import upsert_user_match, upsert_enemy_profile, upsert_map_cache, get_map_name
from api.rivals_client import (
    get_match_history, get_match_detail, get_match_details_batch,
    get_player_stats, get_map_list, get_enemies_from_match,
)
from analysis.user_signals import get_hero_winrates, get_hero_winrates_on_map, classify_comp, get_winrate_vs_archetype
from analysis.enemy_signals import get_enemy_weaknesses, aggregate_enemy_vulnerabilities
from analysis.meta_signals import get_rank_winrates, get_map_winrates, compute_personal_vs_community_delta
from llm.prompt_builder import build_context
from llm.recommender import get_recommendation
from cli.output import (
    console, print_header, print_recommendation, print_hero_stats, print_timing, print_error, print_info
)


def parse_args():
    p = argparse.ArgumentParser(description="Marvel Rivals Counter-Pick Engine")
    p.add_argument("--user", required=True, help="Your Marvel Rivals username")
    p.add_argument("--ingest", action="store_true", help="Pull and store match history + enemy profiles")
    p.add_argument("--enemies", help="Comma-separated enemy usernames (manual mode)")
    p.add_argument("--map", dest="map_name", help="Current map name")
    p.add_argument("--rank", default="Gold", help="Your rank tier (default: Gold)")
    p.add_argument("--cv", action="store_true", help="Auto-detect enemy names via screen capture OCR")
    p.add_argument("--stats", action="store_true", help="Print your hero win rate stats")
    return p.parse_args()


async def run_ingest(username: str, conn):
    print_info(f"Fetching match history for {username}...")
    t0 = time.time()

    matches = await get_match_history(username, limit=50)
    print_info(f"Found {len(matches)} matches. Fetching match details...")

    map_data = await get_map_list()
    for map_id, map_name in map_data.items():
        upsert_map_cache(conn, int(map_id), map_name)

    match_uids = [m.get("match_uid") or m.get("id") for m in matches if m.get("match_uid") or m.get("id")]
    details = await get_match_details_batch(match_uids)

    user_uid = None
    for match, detail in zip(matches, details):
        if isinstance(detail, Exception):
            continue

        map_id = match.get("map_id") or match.get("match_map_id")
        resolved_map = get_map_name(conn, map_id) if map_id else None
        result = "win" if match.get("is_win") else "loss"

        # Detect user_uid from match detail on first successful match
        if user_uid is None:
            players = detail.get("match_players", detail.get("players", []))
            for p in players:
                if (p.get("nick_name") or "").lower() == username.lower():
                    user_uid = p.get("player_uid") or p.get("uid")
                    break

        enemies = get_enemies_from_match(detail, user_uid) if user_uid else []

        upsert_user_match(conn, {
            "match_uid": match.get("match_uid") or match.get("id"),
            "player_username": username,
            "player_uid": user_uid,
            "hero_played": match.get("hero_played") or match.get("hero", "Unknown"),
            "map_id": map_id,
            "map_name": resolved_map,
            "result": result,
            "enemy_comp": [e["nick_name"] for e in enemies],
            "enemy_uids": [e["uid"] for e in enemies if e.get("uid")],
            "enemy_usernames": [e["nick_name"] for e in enemies],
            "kills": match.get("kills"),
            "deaths": match.get("deaths"),
            "assists": match.get("assists"),
            "season": str(match.get("season", "")),
            "game_mode_id": match.get("game_mode"),
            "played_at": match.get("match_time_stamp") or match.get("played_at"),
        })

    elapsed = time.time() - t0
    print_info(f"Ingestion complete in {elapsed:.1f}s. {len(matches)} matches stored.")


async def run_recommend(args, conn):
    timings = {}

    # Enemy detection
    t0 = time.time()
    if args.cv:
        from cv.ocr import extract_all_enemy_names
        enemy_usernames = extract_all_enemy_names()
        if not enemy_usernames:
            print_error("OCR detected no enemy names. Fall back to --enemies flag.")
            return
        detected_via = "ocr"
    elif args.enemies:
        enemy_usernames = [e.strip() for e in args.enemies.split(",")]
        detected_via = "manual"
    else:
        print_error("Provide --enemies or --cv to identify the enemy team.")
        return
    timings["Enemy detection"] = time.time() - t0

    map_name = args.map_name or "Unknown Map"
    print_header(args.user, map_name, enemy_usernames)

    # Fetch enemy profiles (PREMIUM)
    t0 = time.time()
    print_info("Fetching enemy profiles...")
    for uname in enemy_usernames:
        try:
            profile = await get_player_stats(uname)
            if not profile or profile.get("isPrivate"):
                continue
            hero_stats = profile.get("hero_stats", profile.get("heroes", []))
            for hs in hero_stats:
                hero_name = hs.get("hero_name") or hs.get("name", "")
                games = hs.get("games_played") or hs.get("matches", 0)
                wins = hs.get("wins", 0)
                losses = games - wins
                wr = round(wins / games, 4) if games > 0 else 0.0
                upsert_enemy_profile(conn, uname, uname, {
                    "hero_name": hero_name,
                    "games_played": games,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": wr,
                }, season="current")
        except Exception:
            pass
    timings[f"API lookups ({len(enemy_usernames)} enemies)"] = time.time() - t0

    # Analysis
    t0 = time.time()
    personal_wr = get_hero_winrates(conn, args.user)
    map_wr_personal = get_hero_winrates_on_map(conn, args.user, map_name)
    comp_archetype = classify_comp(enemy_usernames)
    archetype_winrates = get_winrate_vs_archetype(conn, args.user, comp_archetype)
    community_rank_wr = get_rank_winrates(conn, args.rank)
    community_map_wr = get_map_winrates(conn, map_name, args.rank)
    personal_vs_community = compute_personal_vs_community_delta(personal_wr, community_rank_wr)
    enemy_signals = get_enemy_weaknesses(conn, enemy_usernames)
    enemy_vulnerabilities = aggregate_enemy_vulnerabilities(enemy_signals)
    timings["Analysis computation"] = time.time() - t0

    # LLM
    t0 = time.time()
    prompt = build_context(
        username=args.user,
        player_rank=args.rank,
        map_name=map_name,
        enemy_heroes=enemy_usernames,
        comp_archetype=comp_archetype,
        personal_vs_community=personal_vs_community,
        archetype_winrates=archetype_winrates,
        enemy_signals=enemy_signals,
        enemy_vulnerabilities=enemy_vulnerabilities,
        map_winrates=community_map_wr,
    )
    log_meta = {
        "player_username": args.user,
        "map_name": map_name,
        "enemy_uids": [],
        "enemy_usernames": enemy_usernames,
        "detected_via": detected_via,
    }
    recommendation = get_recommendation(prompt, conn=conn, log_meta=log_meta)
    timings["LLM inference"] = time.time() - t0

    print_recommendation(recommendation)
    print_timing(timings)


async def main():
    if not DATABASE_URL:
        console.print("[bold red]DATABASE_URL not set. Check your .env file.[/]")
        return

    args = parse_args()
    init_pool()
    conn = get_conn()

    try:
        if args.ingest:
            await run_ingest(args.user, conn)

        if args.stats:
            stats = get_hero_winrates(conn, args.user)
            print_hero_stats(stats, title=f"{args.user}'s Hero Win Rates")

        if args.enemies or args.cv:
            await run_recommend(args, conn)
    finally:
        release_conn(conn)


if __name__ == "__main__":
    asyncio.run(main())
