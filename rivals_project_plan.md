# MRLens — Marvel Rivals Pick Advisor
### Project Plan v2.0 — Map/Side/Team-Comp Focused

---

## Vision

A terminal-based hero recommendation engine that answers one question mid-lobby:

> **"Given this map, this side, and these teammates — what should I play?"**

### Core signals, in priority order

1. **Map** — your personal win rate per hero on this specific map
2. **Side** — attack vs defense changes which heroes thrive (payload push vs hold)
3. **Ally comp** — your teammates' heroes; avoid role overlap, maximize team-up synergies
4. **Personal history** — your overall win rate per hero, flagging low-sample heroes
5. **Community meta** — public hero win rates at your rank on this map, as a baseline

**Enemy player profile lookups are deferred.** They require premium API calls (6 per session) and add latency. Once API access is better understood, enemy WR analysis will be added as a later phase.

No frontend. Runs locally. Triggered mid-lobby. Output is a clean CLI printout.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRY POINTS                             │
│                                                                 │
│   [Manual Mode]              [CV Mode]                          │
│   python main.py             python main.py --cv                │
│   --user "SamirAli"          --user "SamirAli"                  │
│   --map "Tokyo 2099"         (auto-detects map + ally heroes)   │
│   --side attack                                                 │
│   --allies "Thor,Loki,..."                                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CV LAYER (Phase 3)                           │
│   Screen capture → OCR → Map name, side, ally hero names       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                         │
│                                                                 │
│   SOURCE A — MarvelRivalsAPI (personal match history)           │
│   STEP 1: /api/v2/player/{user}/match-history                   │
│           → match_uid, hero_played, is_win, map_id, side        │
│   STEP 2: /api/v1/match/{match_uid}                             │
│           → ally heroes (same camp), map resolution             │
│   STEP 3: /api/v1/heroes/hero/{name}                            │
│           → hero role, team-up abilities (synergy data)         │
│   STEP 4: /api/v1/maps                                          │
│           → map_id → map_name cache                             │
│                                                                 │
│   SOURCE B — Official MR Hero Hot List                          │
│   marvelrivals.com/heroes_data/ → hero win rate + pick rate     │
│   → cached daily, keyed by (hero, rank_tier, game_mode)         │
│                                                                 │
│   SOURCE C — counterwatch.gg (map-specific win rates)           │
│   counterwatch.gg/stats/marvel-rivals/maps → per-hero WR/map   │
│   → cached daily, keyed by (hero, map_name, rank_tier)         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                │
│   PostgreSQL:                                                   │
│   - user_matches         (personal match history + side/allies) │
│   - hero_synergies       (team-up pairs from API, cached)       │
│   - meta_win_rates_rank  (public: hero WR by rank, global)      │
│   - meta_win_rates_map   (public: hero WR by map + rank)        │
│   - map_cache            (map_id → map_name + map type)         │
│   - recommendation_log   (every session prompt + output)        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER                               │
│                                                                 │
│   MAP signals:                                                  │
│   - Win rate per hero on this specific map                      │
│   - Win rate per hero on this map + side (attack/defense)       │
│   - Map archetype: escort, control, hybrid, convoy              │
│                                                                 │
│   ALLY COMP signals:                                            │
│   - Role coverage: are healer/tank/dps slots filled?            │
│   - Team-up synergy: does any ally hero unlock a team-up?       │
│   - Avoid role overlap with existing allies                     │
│                                                                 │
│   PERSONAL signals:                                             │
│   - Overall win rate per hero                                   │
│   - Win rate per hero on this map                               │
│   - Win rate per hero on this map + side                        │
│   - Games played threshold (flag low-sample heroes)             │
│                                                                 │
│   PUBLIC COMPARISON signals:                                    │
│   - Community win rate at user's rank on this map               │
│   - Delta: personal WR vs community WR (skill edge indicator)   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM RECOMMENDATION LAYER                     │
│   Anthropic API → Structured prompt → Ranked picks + reasoning  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLI OUTPUT                                   │
│   Ranked hero suggestions with per-pick reasoning               │
│   Includes: personal WR, map WR, side note, synergy callout    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | Best CV/ML ecosystem |
| Screen Capture | `mss` | Fast cross-platform screenshot |
| OCR | `EasyOCR` | Accurate on stylized game fonts |
| API Client | `httpx` (async) | Async HTTP for multi-lookup |
| Database | PostgreSQL | Time-series friendly, local |
| ORM | `psycopg2` + raw SQL | Lightweight, direct SQL control |
| LLM | Anthropic API (Claude) | Strong structured reasoning |
| CLI | `argparse` + `rich` | Clean colored terminal output |
| Config | `.env` + `python-dotenv` | Standard secrets management |
| Dependency Mgmt | `pip` + `requirements.txt` | Simple |

---

## Project File Structure

```
MRLens/
│
├── main.py                       # Entry point, arg parsing, orchestration
│
├── config/
│   └── settings.py               # Loads .env, constants, validation
│
├── cv/
│   ├── capture.py                # Screen capture via mss
│   ├── ocr.py                    # EasyOCR pipeline
│   └── regions.py                # Screen region coordinates per resolution
│
├── api/
│   ├── rivals_client.py          # MarvelRivalsAPI wrapper
│   ├── hotlist_client.py         # Scraper: MR Hero Hot List (rank win rates)
│   └── counterwatch_client.py    # Scraper: counterwatch.gg (map win rates)
│
├── db/
│   ├── connection.py             # PostgreSQL connection pool
│   ├── schema.sql                # Full schema definition
│   └── queries.py                # All read/write query functions
│
├── analysis/
│   ├── user_signals.py           # Personal win rates per hero, map, side
│   ├── ally_signals.py           # Role coverage, team-up synergy detection
│   └── meta_signals.py           # Community win rates, personal vs meta delta
│
├── llm/
│   ├── prompt_builder.py         # Builds structured LLM prompt
│   └── recommender.py            # Calls Anthropic API, parses response
│
├── cli/
│   └── output.py                 # Rich-formatted terminal output
│
├── tests/
│   ├── test_analysis.py
│   ├── test_ally_signals.py
│   └── test_recommender.py
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## Database Schema

```sql
-- Tracks every game the user has played
CREATE TABLE IF NOT EXISTS user_matches (
    id                  SERIAL PRIMARY KEY,
    match_uid           VARCHAR(64) UNIQUE NOT NULL,
    player_username     VARCHAR(64) NOT NULL,
    player_uid          BIGINT,
    hero_played         VARCHAR(64) NOT NULL,
    map_id              INT,
    map_name            VARCHAR(128),
    side                VARCHAR(8) CHECK (side IN ('attack', 'defense', 'unknown')),
    result              VARCHAR(8) NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
    ally_heroes         TEXT[],          -- teammates' heroes (same camp)
    enemy_comp          TEXT[],          -- enemy heroes (for future use)
    enemy_uids          BIGINT[],
    enemy_usernames     TEXT[],
    kills               INT,
    deaths              INT,
    assists             INT,
    season              VARCHAR(16),
    game_mode_id        INT,
    played_at           TIMESTAMPTZ,
    ingested_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Hero team-up synergy pairs (from /api/v1/heroes/hero/{name}, cached)
CREATE TABLE IF NOT EXISTS hero_synergies (
    id                  SERIAL PRIMARY KEY,
    hero_name           VARCHAR(64) NOT NULL,
    ally_hero           VARCHAR(64) NOT NULL,
    synergy_name        VARCHAR(128),
    cached_at           TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, ally_hero)
);

-- Public meta: hero win rates by rank (global)
CREATE TABLE IF NOT EXISTS meta_win_rates_rank (
    id                  SERIAL PRIMARY KEY,
    hero_name           VARCHAR(64) NOT NULL,
    rank_tier           VARCHAR(32) NOT NULL,
    game_mode           VARCHAR(16) NOT NULL,
    win_rate            DECIMAL(5,2),
    pick_rate           DECIMAL(5,2),
    recorded_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, rank_tier, game_mode)
);

-- Public meta: hero win rates per map per rank (counterwatch.gg)
CREATE TABLE IF NOT EXISTS meta_win_rates_map (
    id                  SERIAL PRIMARY KEY,
    hero_name           VARCHAR(64) NOT NULL,
    map_name            VARCHAR(128) NOT NULL,
    rank_tier           VARCHAR(32) NOT NULL DEFAULT 'All',
    win_rate            DECIMAL(5,2),
    source              VARCHAR(32) DEFAULT 'counterwatch',
    recorded_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, map_name, rank_tier)
);

-- Map ID → name + type cache
CREATE TABLE IF NOT EXISTS map_cache (
    map_id              INT PRIMARY KEY,
    map_name            VARCHAR(128) NOT NULL,
    map_type            VARCHAR(32),     -- escort, control, hybrid, convoy
    cached_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Enemy player profiles — deferred to later phase (requires premium API)
CREATE TABLE IF NOT EXISTS enemy_profiles (
    id                  SERIAL PRIMARY KEY,
    player_uid          BIGINT NOT NULL,
    player_username     VARCHAR(64),
    hero_name           VARCHAR(64) NOT NULL,
    games_played        INT DEFAULT 0,
    wins                INT DEFAULT 0,
    losses              INT DEFAULT 0,
    win_rate            DECIMAL(5,2),
    season              VARCHAR(16),
    is_private          BOOLEAN DEFAULT FALSE,
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (player_uid, hero_name, season)
);

-- Logs each recommendation session
CREATE TABLE IF NOT EXISTS recommendation_log (
    id                  SERIAL PRIMARY KEY,
    player_username     VARCHAR(64),
    map_name            VARCHAR(128),
    side                VARCHAR(8),
    ally_heroes         TEXT[],
    detected_via        VARCHAR(16) CHECK (detected_via IN ('manual', 'ocr')),
    llm_prompt          TEXT,
    llm_response        TEXT,
    recommended_heroes  TEXT[],
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_matches_player     ON user_matches (player_username);
CREATE INDEX IF NOT EXISTS idx_user_matches_hero       ON user_matches (hero_played);
CREATE INDEX IF NOT EXISTS idx_user_matches_map        ON user_matches (map_name);
CREATE INDEX IF NOT EXISTS idx_user_matches_side       ON user_matches (side);
CREATE INDEX IF NOT EXISTS idx_user_matches_result     ON user_matches (result);
CREATE INDEX IF NOT EXISTS idx_synergies_hero          ON hero_synergies (hero_name);
CREATE INDEX IF NOT EXISTS idx_meta_rank_hero          ON meta_win_rates_rank (hero_name, rank_tier);
CREATE INDEX IF NOT EXISTS idx_meta_map_hero           ON meta_win_rates_map (hero_name, map_name, rank_tier);
```

---

## Environment Variables

```bash
# .env.example

# MarvelRivalsAPI
RIVALS_API_KEY=your_key_here
RIVALS_API_BASE_URL=https://marvelrivalsapi.com/api/v1

# Anthropic
ANTHROPIC_API_KEY=your_key_here

# PostgreSQL
DATABASE_URL=postgresql://user@localhost:5432/rivals_db

# OCR Settings
SCREEN_RESOLUTION=1920x1080
OCR_CONFIDENCE_THRESHOLD=0.6
```

---

## Phase 1 — Core Data Pipeline

**Goal:** Pull personal match history, resolve allies per match, store in PostgreSQL.

### Tasks

**1.1 — Project setup** ✅
- Repo `MRLens` live on GitHub (`samirali123`)
- Virtual environment + `requirements.txt`
- `.env` configured, `.gitignore` securing secrets
- PostgreSQL running locally, schema applied

**1.2 — API client (`api/rivals_client.py`)** ✅
- `get_match_history` — paginated match list
- `get_match_detail` — full lobby (all 12 players, camps, heroes)
- `get_match_details_batch` — async batch fetch
- `get_hero_details` — role, team-up abilities
- `get_map_list` — map_id → name cache
- `get_allies_from_match` — filter same-camp players (new, replaces get_enemies)
- Rate limiting with exponential backoff

**1.3 — DB layer (`db/queries.py`)** ✅
- `upsert_user_match` — now includes `side` and `ally_heroes` columns
- `upsert_map_cache`, `get_map_name`
- `get_user_hero_stats`, `get_user_hero_stats_by_map`
- `upsert_hero_synergy`, `get_synergies_for_hero`

**1.4 — Ingestion script**
- Pull match history
- For each match: resolve allies (same camp), resolve map name, determine side
- Upsert to `user_matches` with ally_heroes populated
- Cache hero team-up synergies from hero detail calls

**Deliverable:** `python main.py --user "SamirAli" --ingest` populates the DB with match history, ally comps, and hero synergy data.

---

## Phase 2 — Analysis + LLM Recommendation

**Goal:** Given a username + map + side + ally heroes, output ranked hero picks with reasoning.

### Tasks

**2.1 — User signals (`analysis/user_signals.py`)**
```python
def get_hero_winrates(conn, username) -> dict
    # Overall win rate per hero

def get_hero_winrates_on_map(conn, username, map_name) -> dict
    # Win rate per hero filtered to this map

def get_hero_winrates_on_map_and_side(conn, username, map_name, side) -> dict
    # Win rate per hero on this map + attack or defense
    # Most specific signal — weighted highest in the prompt
```

**2.2 — Ally signals (`analysis/ally_signals.py`)**
```python
def get_role_coverage(ally_heroes: list[str], hero_roles: dict) -> dict
    # Returns: {"tank": 1, "healer": 1, "dps": 3}
    # Flags if a role slot is missing

def get_synergy_opportunities(conn, ally_heroes: list[str]) -> list[dict]
    # Queries hero_synergies table
    # Returns heroes that unlock a team-up with an existing ally
    # e.g. "Thor is on your team — Captain America unlocks Thunderstrike"

def suggest_role_fill(role_coverage: dict) -> str | None
    # If team has no healer, returns "healer"
    # If balanced, returns None
```

**2.3 — Meta signals (`analysis/meta_signals.py`)**
```python
def get_rank_winrates(conn, rank_tier, game_mode) -> dict
def get_map_winrates(conn, map_name, rank_tier) -> dict
def compute_personal_vs_community_delta(personal, community) -> dict
```

**2.4 — Prompt builder (`llm/prompt_builder.py`)**

```
You are a Marvel Rivals coach. Recommend the top 3 hero picks for this player.

PLAYER: {username}
RANK: {rank}
MAP: {map_name}  ({map_type} — escort/control/hybrid/convoy)
SIDE: {side}  (attack / defense)
ALLY HEROES: {ally_heroes}
ROLE COVERAGE: {role_coverage}  e.g. Tank ✓, Healer ✗, DPS ✓✓✓

SYNERGY OPPORTUNITIES (heroes that unlock a team-up with an ally):
{synergy_list}

PLAYER WIN RATES — map + side specific (weighted most heavily):
{map_side_winrates}

PLAYER WIN RATES — this map overall:
{map_winrates}

PLAYER WIN RATES — overall:
{overall_winrates}
(heroes with <10 games marked [LOW SAMPLE])

COMMUNITY WIN RATES ON {map_name} at {rank}:
{community_map_winrates}

INSTRUCTIONS:
- Prioritize map+side specific win rate above all else
- Flag if a pick fills a missing role (especially healer)
- Flag if a pick activates a team-up synergy with an ally
- Flag positive delta vs community (skill edge)
- Avoid suggesting heroes already on the ally team

Respond in this exact format:
1. [Hero Name] — [Reason]
2. [Hero Name] — [Reason]
3. [Hero Name] — [Reason]
```

**2.5 — CLI flags**
```bash
python main.py --user "SamirAli" --map "Tokyo 2099" --side attack --allies "Thor,Loki,Luna Snow,Hawkeye" --rank Gold
```

**Deliverable:** Clean ranked recommendation printed to terminal, grounded in map/side/team context.

---

## Phase 3 — Computer Vision Layer

**Goal:** Auto-detect map name, side, and ally hero names from the loading screen — so the user doesn't have to type anything.

### What to detect

The Marvel Rivals loading screen shows:
- **Map name** — displayed prominently at top center
- **Side** — "Attack" or "Defense" label visible during loading
- **Your team's hero portraits** — left side of the screen (your camp)

### Tasks

**3.1 — Region calibration (`cv/regions.py`)**
Define bounding boxes per resolution for:
- Map name text region
- Side indicator region (attack/defense label)
- Ally hero name slots (5 teammates)

**3.2 — Screen capture (`cv/capture.py`)** ✅
- `capture_region(region)` — returns numpy array
- `capture_all_ally_regions()` — captures all 5 ally hero slots
- `capture_map_region()` — captures map name region
- `capture_side_region()` — captures attack/defense indicator

**3.3 — OCR pipeline (`cv/ocr.py`)** ✅
- `extract_name_from_region(image)` — single region → cleaned string
- `extract_all_ally_names()` — all 5 ally slots → list of names
- `extract_map_name()` — map name region → string
- `extract_side()` — returns "attack" or "defense" from OCR result

**3.4 — Calibration tool (`calibrate.py`)**
Interactive script: screenshot → click to mark regions → outputs coordinates for `regions.py`.

**Deliverable:** `python main.py --user "SamirAli" --cv` takes a screenshot, reads map/side/allies, runs full recommendation. Zero manual input required.

---

## Phase 4 — Enemy Analysis (Deferred)

**Goal:** Add enemy player profile lookups once API access is better understood and call budget is confirmed.

This phase requires premium API access (`/api/v2/player/{uid}` — 1 call per enemy player, 6 per session).

### What it adds
- Which heroes each enemy player personally loses to most
- Cross-enemy aggregation: which hero exploits the most opponents simultaneously
- Additional LLM signal: "Storm also counters 4 of 6 enemy players based on their history"

### Why it's deferred
- 6 premium calls per session adds cost and latency
- The map/side/team signals already provide strong recommendations
- Enemy profile data needs a confirmed API tier and rate limit budget before building around it

---

## Phase 5 — Polish + Resume Packaging

**4.1 — README.md** ✅ (see README.md)

**4.2 — Demo mode**
`--demo` flag runs with pre-loaded fixture data (no API key needed). Shows off the tool in interviews without live credentials.

**4.3 — Error handling**
- API timeout / rate limit fallback
- OCR no-detection fallback → prompt manual input
- Missing map data fallback → use overall stats only
- DB connection failure handling

**4.4 — Performance logging**
```
[INFO] OCR extraction:        1.2s
[INFO] API lookups:           2.1s
[INFO] Analysis computation:  0.1s
[INFO] LLM inference:         2.3s
[INFO] Total:                 5.7s
```

---

## Resume Bullet Points (draft)

```
MRLens — Marvel Rivals Pick Advisor | Python, PostgreSQL, EasyOCR, Anthropic API
• Built a real-time hero recommendation CLI that reads map, side (attack/defense),
  and ally hero composition from the loading screen via OCR, then recommends the
  best picks grounded in personal win-rate history per map and side, team-up synergy
  detection, and community meta win rates — all fed into a structured LLM prompt.
• Designed a PostgreSQL schema tracking per-hero win rates split by map and
  attack/defense side, with composite indexes enabling sub-10ms cross-filtering
  across hero, map, side, and result.
• Implemented an OCR preprocessing pipeline (grayscale, CLAHE, adaptive thresholding)
  to reliably extract stylized in-game text from screen regions across variable
  background conditions.
```

---

## API Reference — Confirmed Endpoints

| Endpoint | Tier | Used For |
|---|---|---|
| `GET /api/v2/player/{user}/match-history` | Free | Pull user's match list |
| `GET /api/v1/match/{match_uid}` | Free | Ally heroes, map, full lobby |
| `GET /api/v1/heroes/hero/{name}` | Free | Role, team-up synergies |
| `GET /api/v1/heroes/hero/{name}/stats` | Free | Global hero win rate |
| `GET /api/v1/maps` | Free | Map ID → name cache |
| `GET /api/v2/player/{uid}` | **Premium** | Enemy player profiles (Phase 4) |

### Remaining Unknowns (validate with live API key)

| Question | Impact |
|---|---|
| Does match detail expose which side (attack/defense) each team was on? | Core to Phase 1 — may need to infer from game_mode or map_type |
| Does `player_heroes` show all heroes played or just final? | Affects ally comp accuracy |
| Are team-up pairs documented in hero detail response? | Determines if synergy table can be populated from API |
| Free tier rate limit: per minute or per day? | Determines async batch throttling |

---

## Stretch Goals

- **Discord bot:** Expose as a slash command, query mid-lobby from phone
- **Enemy analysis:** Phase 4 — add enemy player WR lookups once API budget confirmed
- **Patch tracking:** Auto-detect stale meta cache based on patch date
- **Win prediction:** Logistic regression on comp matchups after enough logged matches
- **Draft order awareness:** Adjust picks based on late-pick position

---

*Plan v2.0 — Refocused on map/side/team-comp as primary signals. Enemy player profile lookups deferred to Phase 4. Ally hero detection added to CV layer.*
