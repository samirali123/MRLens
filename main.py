import argparse
import asyncio
import time

from config.settings import DATABASE_URL, validate_env
from db.connection import init_pool, get_conn, release_conn
from db.queries import upsert_user_match, upsert_map_cache, get_map_name, get_user_hero_stats
from api.rivals_client import (
    get_match_history, get_match_details_batch,
    get_allies_from_match, get_enemies_from_match, get_map_list,
)
from analysis.user_signals import get_hero_winrates, get_hero_winrates_on_map, classify_comp
from analysis.ally_signals import (
    get_all_hero_pair_winrates, get_top_synergies_for_hero,
    get_best_heroes_on_map, get_synergy_opportunities,
)
from analysis.meta_signals import get_rank_winrates, get_map_winrates, compute_personal_vs_community_delta
from llm.prompt_builder import build_context
from llm.recommender import get_recommendation
from cli.output import (
    console, print_header, print_recommendation, print_hero_stats, print_timing, print_error, print_info
)


def parse_args():
    p = argparse.ArgumentParser(description="MRLens — Marvel Rivals Pick Advisor")
    p.add_argument("--uid", required=True, type=int, help="Your Marvel Rivals player UID")
    p.add_argument("--username", default="Player", help="Your display name (for output only)")
    p.add_argument("--ingest", action="store_true", help="Pull and store match history")
    p.add_argument("--map", dest="map_name", help="Current map name")
    p.add_argument("--side", choices=["attack", "defense"], help="Attack or defense")
    p.add_argument("--allies", help="Comma-separated ally hero names")
    p.add_argument("--rank", default="Gold", help="Your rank tier (default: Gold)")
    p.add_argument("--cv", action="store_true", help="Auto-detect map/side/allies via screen capture")
    p.add_argument("--stats", action="store_true", help="Print your hero win rate stats")
    p.add_argument("--synergies", metavar="HERO", help="Show your personal synergy data for a hero")
    p.add_argument("--pairs", action="store_true", help="Show all your hero pair win rates")
    return p.parse_args()


async def run_ingest(uid: int, username: str, conn):
    print_info(f"Fetching match history for UID {uid}...")
    t0 = time.time()

    matches = await get_match_history(str(uid), limit=50)
    if not matches:
        print_error("No matches returned. Profile may be private or UID incorrect.")
        return

    print_info(f"Found {len(matches)} matches. Caching map data...")
    map_data = await get_map_list()
    for map_id, map_name in map_data.items():
        upsert_map_cache(conn, int(map_id), map_name)

    match_uids = [m.get("match_uid") or m.get("id") for m in matches if m.get("match_uid") or m.get("id")]
    print_info(f"Fetching {len(match_uids)} match details (allies, maps, sides)...")
    details = await get_match_details_batch(match_uids)

    stored = 0
    for match, detail in zip(matches, details):
        if isinstance(detail, Exception) or not detail:
            continue

        map_id = match.get("map_id") or match.get("match_map_id")
        resolved_map = get_map_name(conn, map_id) if map_id else None
        result = "win" if match.get("is_win") else "loss"

        allies = get_allies_from_match(detail, uid)
        ally_hero_names = [a["hero"] for a in allies if a.get("hero")]

        # Side detection — try game_mode_id or map type heuristics; default unknown
        side = _detect_side(match, detail)

        upsert_user_match(conn, {
            "match_uid": match.get("match_uid") or match.get("id"),
            "player_username": username,
            "player_uid": uid,
            "hero_played": match.get("hero_played") or match.get("hero", "Unknown"),
            "map_id": map_id,
            "map_name": resolved_map,
            "side": side,
            "result": result,
            "ally_heroes": ally_hero_names,
            "enemy_comp": [],
            "enemy_uids": [],
            "enemy_usernames": [],
            "kills": match.get("kills"),
            "deaths": match.get("deaths"),
            "assists": match.get("assists"),
            "season": str(match.get("season", "")),
            "game_mode_id": match.get("game_mode"),
            "played_at": match.get("match_time_stamp") or match.get("played_at"),
        })
        stored += 1

    elapsed = time.time() - t0
    print_info(f"Ingestion complete in {elapsed:.1f}s — {stored} matches stored.")


def _detect_side(match: dict, detail: dict) -> str:
    """Best-effort side detection from available match data."""
    side_raw = (
        match.get("side")
        or detail.get("side")
        or match.get("team_side")
        or detail.get("team_side")
    )
    if isinstance(side_raw, str):
        s = side_raw.lower()
        if s in ("attack", "offense"):
            return "attack"
        if s in ("defense", "defend"):
            return "defense"
    return "unknown"


def _print_synergies(conn, uid: int, hero: str):
    results = get_top_synergies_for_hero(conn, uid, hero)
    if not results:
        console.print(f"[yellow]Not enough data yet for {hero} synergies (need 3+ games per ally).[/]")
        return
    console.print(f"\n[bold cyan]Your {hero} synergies (allies ranked by your win rate):[/]")
    console.print(f"{'Ally':<22} {'Games':>6} {'Win Rate':>10} {'vs Baseline':>13}")
    console.print("─" * 55)
    for s in results:
        delta_str = f"{s['delta']:+.1%}" if s["delta"] is not None else "N/A"
        color = "green" if (s["delta"] or 0) > 0 else "red"
        console.print(
            f"{s['ally']:<22} {s['games']:>6} {s['win_rate']:>9.1%} [{color}]{delta_str:>13}[/]"
        )
    if results:
        baseline = results[0]["baseline_wr"]
        console.print(f"\n[dim]Baseline {hero} win rate: {baseline:.1%}[/]")


def _print_all_pairs(conn, uid: int):
    pairs = get_all_hero_pair_winrates(conn, uid)
    if not pairs:
        console.print("[yellow]Not enough pair data yet (need 3+ games per combination).[/]")
        return
    console.print("\n[bold cyan]Your hero pair win rates:[/]")
    console.print(f"{'You':<20} {'+ Ally':<22} {'Games':>6} {'Win Rate':>10}")
    console.print("─" * 62)
    for p in pairs:
        wr = float(p["win_rate"])
        color = "green" if wr >= 0.55 else "red" if wr < 0.45 else "yellow"
        console.print(
            f"{p['hero_played']:<20} {p['ally']:<22} {int(p['games']):>6} [{color}]{wr:>9.1%}[/]"
        )


async def run_recommend(args, conn):
    timings = {}

    t0 = time.time()
    if args.cv:
        from cv.ocr import extract_all_ally_names, extract_map_name, extract_side
        ally_heroes = extract_all_ally_names()
        map_name = extract_map_name() or "Unknown Map"
        side = extract_side() or "unknown"
        detected_via = "ocr"
    else:
        ally_heroes = [h.strip() for h in args.allies.split(",")] if args.allies else []
        map_name = args.map_name or "Unknown Map"
        side = args.side or "unknown"
        detected_via = "manual"
    timings["Input detection"] = time.time() - t0

    print_header(args.username, map_name, ally_heroes)

    t0 = time.time()
    personal_wr = get_hero_winrates(conn, args.uid)
    map_wr = get_best_heroes_on_map(conn, args.uid, map_name, side)
    overall_wr = get_hero_winrates(conn, args.uid)
    community_rank_wr = get_rank_winrates(conn, args.rank)
    community_map_wr = get_map_winrates(conn, map_name, args.rank)
    personal_vs_community = compute_personal_vs_community_delta(personal_wr, community_rank_wr)

    # Synergy: for each of my top heroes, which active allies boost my win rate?
    active_synergies = []
    top_heroes = sorted(personal_wr.items(), key=lambda x: x[1]["win_rate"], reverse=True)[:8]
    for hero, _ in top_heroes:
        syns = get_synergy_opportunities(conn, args.uid, hero, ally_heroes)
        for s in syns:
            active_synergies.append({"hero": hero, **s})

    comp_archetype = classify_comp(ally_heroes)
    timings["Analysis computation"] = time.time() - t0

    t0 = time.time()
    prompt = build_context(
        username=args.username,
        player_rank=args.rank,
        map_name=map_name,
        side=side,
        ally_heroes=ally_heroes,
        comp_archetype=comp_archetype,
        personal_vs_community=personal_vs_community,
        map_winrates={r["hero_played"]: float(r["win_rate"]) for r in map_wr},
        community_map_winrates=community_map_wr,
        active_synergies=active_synergies,
    )
    log_meta = {
        "player_username": args.username,
        "map_name": map_name,
        "side": side,
        "ally_heroes": ally_heroes,
        "enemy_uids": [],
        "enemy_usernames": [],
        "detected_via": detected_via,
    }
    recommendation = get_recommendation(prompt, conn=conn, log_meta=log_meta)
    timings["LLM inference"] = time.time() - t0

    print_recommendation(recommendation)
    print_timing(timings)


async def main():
    args = parse_args()
    try:
        validate_env()
    except EnvironmentError as e:
        console.print(f"[bold red]{e}[/]")
        return

    init_pool()
    conn = get_conn()

    try:
        if args.ingest:
            await run_ingest(args.uid, args.username, conn)

        if args.stats:
            stats = get_hero_winrates(conn, args.uid)
            print_hero_stats(stats, title=f"{args.username}'s Hero Win Rates")

        if args.synergies:
            _print_synergies(conn, args.uid, args.synergies)

        if args.pairs:
            _print_all_pairs(conn, args.uid)

        if args.allies or args.cv:
            await run_recommend(args, conn)
    finally:
        release_conn(conn)


if __name__ == "__main__":
    asyncio.run(main())
