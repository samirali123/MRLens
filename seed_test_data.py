"""
Generates 1000 realistic unbiased matches using real Marvel Rivals comp
distribution data. No win rate bias per hero or per ally — comp archetype
win rate is the only driver. Records full 6v6 (5 allies + 6 enemies).

Run: python seed_test_data.py
"""
import random
from datetime import datetime, timezone, timedelta
from db.connection import init_pool, get_conn, release_conn
from db.queries import upsert_user_match

UID      = 1554228221
USERNAME = "SamirAli"
SEASON   = "2.0"

# ── Hero pools by role ────────────────────────────────────────────────────────

VANGUARDS = [
    "Hulk", "Doctor Strange", "Groot", "Magneto", "Peni Parker",
    "The Thing", "Venom", "Captain America", "Thor", "Invisible Woman",
    "Mister Fantastic", "Ultron",
]

DUELISTS = [
    "Storm", "Human Torch", "Hawkeye", "Hela", "Black Panther", "Magik",
    "Moon Knight", "Black Widow", "Iron Man", "Squirrel Girl", "Spider-Man",
    "Scarlet Witch", "Winter Soldier", "Star-Lord", "Namor", "Psylocke",
    "Wolverine", "Iron Fist", "Emma Frost", "Phoenix", "The Punisher",
]

STRATEGISTS = [
    "Loki", "Mantis", "Rocket Raccoon", "Cloak & Dagger",
    "Luna Snow", "Adam Warlock", "Jeff the Land Shark",
]

MAPS = [
    "Tokyo 2099", "Yggdrasil", "Symbiotic Surface", "Midtown",
    "Hydra Charteris Base", "Empire of Eternal Night", "Klyntar",
    "Spider-Islands", "Shin-Shibuya", "Intergalactic Insurance",
]

SIDES = ["attack", "defense"]

# ── Comp distribution (vanguards, duelists, strategists) ─────────────────────
# (v, d, s), pick_rate, win_rate
COMP_TABLE = [
    ((2, 2, 2), 0.590, 0.53),
    ((1, 3, 2), 0.160, 0.48),
    ((1, 2, 3), 0.095, 0.45),
    ((2, 1, 3), 0.090, 0.46),
    ((3, 1, 2), 0.014, 0.43),
    ((0, 4, 2), 0.010, 0.25),   # ┐
    ((4, 1, 1), 0.010, 0.25),   # │ "other" split into
    ((3, 3, 0), 0.010, 0.25),   # │ recognisable edge comps
    ((0, 6, 0), 0.010, 0.25),   # ┘
]

_RATES   = [c[1] for c in COMP_TABLE]
_RATE_SUM = sum(_RATES)
_WEIGHTS = [r / _RATE_SUM for r in _RATES]   # normalise to 1.0


def pick_comp() -> tuple[tuple, float]:
    """Return ((v,d,s), win_rate) sampled from the distribution."""
    chosen = random.choices(COMP_TABLE, weights=_WEIGHTS, k=1)[0]
    return chosen[0], chosen[2]


def build_team(comp: tuple[int, int, int], exclude: list[str]) -> list[str]:
    """Fill a 6-player team given (v, d, s) counts, avoiding excluded heroes."""
    v_count, d_count, s_count = comp

    def sample(pool, n, excl):
        available = [h for h in pool if h not in excl]
        return random.sample(available, min(n, len(available)))

    heroes = []
    heroes += sample(VANGUARDS,   v_count, exclude + heroes)
    heroes += sample(DUELISTS,    d_count, exclude + heroes)
    heroes += sample(STRATEGISTS, s_count, exclude + heroes)
    return heroes


def my_hero(comp: tuple[int, int, int], role_choice: str) -> str:
    """Pick my hero matching role_choice and comp slot availability."""
    v, d, s = comp
    if role_choice == "vanguard" and v > 0:
        return random.choice(VANGUARDS)
    if role_choice == "duelist" and d > 0:
        return random.choice(DUELISTS)
    # fallback: pick from whichever role has a slot
    if v > 0:
        return random.choice(VANGUARDS)
    if d > 0:
        return random.choice(DUELISTS)
    return random.choice(STRATEGISTS)


def seed(conn, n: int = 1000):
    now = datetime.now(timezone.utc)
    inserted = 0

    for i in range(n):
        # ── My comp + role ────────────────────────────────────────────────────
        my_comp, my_wr = pick_comp()
        role = "vanguard" if random.random() < 0.80 else "duelist"
        me = my_hero(my_comp, role)

        # ── Allies: fill remaining 5 slots from my comp ───────────────────────
        v, d, s = my_comp
        # subtract my slot
        if me in VANGUARDS:   v -= 1
        elif me in DUELISTS:  d -= 1
        else:                 s -= 1
        ally_comp = (max(v, 0), max(d, 0), max(s, 0))
        allies = build_team(ally_comp, exclude=[me])
        # if comp slots don't total 5, top up with random duelists
        while len(allies) < 5:
            pick = random.choice(DUELISTS)
            if pick not in allies and pick != me:
                allies.append(pick)

        # ── Enemy team ────────────────────────────────────────────────────────
        enemy_comp, _ = pick_comp()
        enemies = build_team(enemy_comp, exclude=[])
        while len(enemies) < 6:
            pick = random.choice(DUELISTS)
            if pick not in enemies:
                enemies.append(pick)

        # ── Result: driven purely by my team's comp win rate ─────────────────
        result = "win" if random.random() < my_wr else "loss"

        # ── Other fields ──────────────────────────────────────────────────────
        map_name  = random.choice(MAPS)
        side      = random.choice(SIDES)
        played_at = now - timedelta(minutes=i * 35)

        upsert_user_match(conn, {
            "match_uid":       f"seed-{i:04d}",
            "player_username": USERNAME,
            "player_uid":      UID,
            "hero_played":     me,
            "map_id":          None,
            "map_name":        map_name,
            "side":            side,
            "result":          result,
            "ally_heroes":     allies,
            "enemy_comp":      enemies,
            "enemy_uids":      [],
            "enemy_usernames": [],
            "kills":           random.randint(1, 22),
            "deaths":          random.randint(0, 14),
            "assists":         random.randint(0, 18),
            "season":          SEASON,
            "game_mode_id":    1,
            "played_at":       played_at.isoformat(),
        })
        inserted += 1

    print(f"Seeded {inserted} matches for {USERNAME} (UID {UID})")
    _print_summary(conn)


def _print_summary(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                hero_played,
                COUNT(*) AS games,
                SUM(CASE WHEN result='win' THEN 1 ELSE 0 END) AS wins,
                ROUND(SUM(CASE WHEN result='win' THEN 1.0 ELSE 0 END)/COUNT(*)*100,1) AS wr_pct
            FROM user_matches
            WHERE player_uid = %s
            GROUP BY hero_played
            ORDER BY games DESC
            LIMIT 12
        """, (UID,))
        rows = cur.fetchall()

    print(f"\n{'Hero':<22} {'Games':>6} {'Wins':>6} {'WR':>7}")
    print("─" * 44)
    for hero, games, wins, wr in rows:
        print(f"{hero:<22} {games:>6} {wins:>6} {wr:>6.1f}%")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT result, COUNT(*) FROM user_matches
            WHERE player_uid = %s GROUP BY result
        """, (UID,))
        totals = dict(cur.fetchall())

    total = sum(totals.values())
    wins  = totals.get("win", 0)
    print(f"\nOverall: {wins}/{total} ({wins/total*100:.1f}% WR)")


if __name__ == "__main__":
    init_pool()
    conn = get_conn()
    try:
        seed(conn)
    finally:
        release_conn(conn)
