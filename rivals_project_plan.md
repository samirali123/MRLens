# Marvel Rivals Counter-Pick Engine
### Project Preparation Document v1.2 — Meta data sources confirmed

---

## Vision

A terminal-based recommendation engine that:
1. Captures the enemy team composition from the screen using computer vision (OCR)
2. Looks up every detected enemy's profile to identify what heroes they personally lose to
3. Cross-references the user's own performance history per hero, per map, per comp type
4. Compares the user's personal stats against community win rates at their rank
5. Feeds all signals into an LLM that outputs ranked hero recommendations with reasoning

**The core philosophy — two lenses on every pick:**
- **Personal lens:** "You personally win 68% on Storm — that's what matters most"
- **Public lens:** "Storm's community win rate at your rank (Gold) is 51% — you're outperforming the meta on her"

This dual-layer comparison grows more accurate the more the user plays, while still being useful on day one via public data.

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
│   --enemies "p1,p2,p3..."    (auto-detects enemy names)         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CV LAYER (Optional)                          │
│   Screen capture → Region crop → OCR → Enemy name list         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                         │
│                                                                 │
│   SOURCE A — MarvelRivalsAPI (personal + enemy data)            │
│   STEP 1: /api/v2/player/{user}/match-history                   │
│           → list of match_uids + user's hero/result per match   │
│   STEP 2: /api/v1/match/{match_uid}  (one call per match)       │
│           → ALL 12 players with nick_name, camp, heroes played  │
│           → filter by opposite camp = enemy usernames + heroes  │
│   STEP 3: /api/v2/player/{enemy_uid}  (PREMIUM)                 │
│           → enemy's hero win/loss breakdown across all seasons  │
│                                                                 │
│   SOURCE B — Official MR Hero Hot List (public meta by rank)    │
│   marvelrivals.com/heroes_data/  → scraped or API-inspected     │
│   → hero win rate + pick rate, filterable by rank + game mode   │
│   → cached daily, keyed by (hero, rank_tier, game_mode)         │
│                                                                 │
│   SOURCE C — counterwatch.gg (map-specific public win rates)    │
│   counterwatch.gg/stats/marvel-rivals/maps  → scraped           │
│   → per-hero win rate on each map, filterable by rank           │
│   → cached daily, keyed by (hero, map_name, rank_tier)          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                │
│   PostgreSQL:                                                   │
│   - user_matches         (personal match history)               │
│   - enemy_profiles       (enemy hero win rates, cached)         │
│   - meta_win_rates_rank  (public: hero WR by rank, global)      │
│   - meta_win_rates_map   (public: hero WR by map + rank)        │
│   - map_cache            (map_id → map_name resolution)         │
│   - recommendation_log   (every session prompt + output)        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER                               │
│                                                                 │
│   PERSONAL signals (from user_matches DB):                      │
│   - Win rate per hero overall                                   │
│   - Win rate per hero on this specific map                      │
│   - Win rate vs comp archetypes (dive, poke, sustain, brawl)    │
│   - Games played threshold (flag low-sample heroes)             │
│                                                                 │
│   ENEMY signals (from enemy_profiles DB):                       │
│   - Which heroes does each enemy lose on most?                  │
│   - Aggregate: which heroes exploit the most enemies at once?   │
│                                                                 │
│   PUBLIC COMPARISON signals (from meta tables):                 │
│   - Community win rate for each candidate hero at user's rank   │
│   - Community win rate on this map at user's rank               │
│   - Delta: personal WR vs community WR (shows skill edge)       │
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
│   Includes: personal WR, community WR, delta, enemy exploit     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | Matches your resume stack, best CV/ML ecosystem |
| Screen Capture | `mss` | Fast cross-platform screenshot library |
| OCR | `EasyOCR` | More accurate than pytesseract on stylized game fonts |
| API Client | `httpx` (async) | Async HTTP, cleaner than requests for multi-lookup |
| Database | PostgreSQL | Matches Cloud Product Catalog, time-series friendly |
| ORM | `psycopg2` + raw SQL | Keeps it lightweight, mirrors your existing SQL skills |
| LLM | Anthropic API (Claude) | You have experience, strong reasoning output |
| CLI | `argparse` + `rich` | `rich` gives clean colored terminal output |
| Config | `.env` + `python-dotenv` | Standard secrets management |
| Dependency Mgmt | `pip` + `requirements.txt` | Simple, resume-appropriate |

---

## Project File Structure

```
rivals-counter-pick/
│
├── main.py                   # Entry point, arg parsing, orchestration
│
├── config/
│   └── settings.py           # Loads .env, constants (API keys, DB URL, screen regions)
│
├── cv/
│   ├── __init__.py
│   ├── capture.py            # Screen capture using mss
│   ├── ocr.py                # EasyOCR pipeline, name extraction
│   └── regions.py            # Screen region coordinates (calibrated per resolution)
│
├── api/
│   ├── __init__.py
│   ├── rivals_client.py      # MarvelRivalsAPI wrapper (player, matches, heroes)
│   ├── hotlist_client.py     # Scraper for official MR Hero Hot List (rank win rates)
│   └── counterwatch_client.py # Scraper for counterwatch.gg (map-specific win rates)
│
├── db/
│   ├── __init__.py
│   ├── connection.py         # PostgreSQL connection pool
│   ├── schema.sql            # Full schema definition
│   └── queries.py            # All read/write query functions
│
├── analysis/
│   ├── __init__.py
│   ├── user_signals.py       # Compute user win rates per hero, map, comp type
│   ├── enemy_signals.py      # Compute enemy loss patterns per hero
│   └── meta_signals.py       # Pull and normalize meta win rates
│
├── llm/
│   ├── __init__.py
│   ├── prompt_builder.py     # Assembles structured context dict → prompt string
│   └── recommender.py        # Calls Anthropic API, parses response
│
├── cli/
│   ├── __init__.py
│   └── output.py             # Rich-formatted terminal output
│
├── tests/
│   ├── test_ocr.py
│   ├── test_api.py
│   ├── test_analysis.py
│   └── test_recommender.py
│
├── .env.example              # Template for required environment variables
├── requirements.txt
└── README.md
```

---

## Database Schema

```sql
-- schema.sql

-- Tracks every game the user has played (pulled from API + manually logged)
CREATE TABLE IF NOT EXISTS user_matches (
    id                  SERIAL PRIMARY KEY,
    match_uid           VARCHAR(64) UNIQUE NOT NULL,
    player_username     VARCHAR(64) NOT NULL,
    player_uid          BIGINT,                      -- from match detail, more stable than username
    hero_played         VARCHAR(64) NOT NULL,
    map_id              INT,                         -- raw int from API (e.g. 1217)
    map_name            VARCHAR(128),                -- resolved from map_id via /api/v1/maps
    result              VARCHAR(8) NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
    enemy_comp          TEXT[],                      -- array of enemy hero names
    enemy_uids          BIGINT[],                    -- array of enemy player UIDs
    enemy_usernames     TEXT[],                      -- array of enemy player names
    kills               INT,
    deaths              INT,
    assists             INT,
    season              VARCHAR(16),                 -- e.g. "1.5"
    game_mode_id        INT,                         -- 1=ranked, 0=quickplay etc
    played_at           TIMESTAMPTZ,
    ingested_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Cached enemy player profiles: their hero win/loss breakdown (from PREMIUM /api/v2/player)
CREATE TABLE IF NOT EXISTS enemy_profiles (
    id                  SERIAL PRIMARY KEY,
    player_uid          BIGINT NOT NULL,             -- prefer UID over username per API docs
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

-- Public meta: hero win rates by rank (global, not map-specific)
-- SOURCE: Official MR Hero Hot List (marvelrivals.com/heroes_data/)
-- Refreshed daily. rank_tier values match official tiers:
-- Bronze, Silver, Gold, Platinum, Diamond, Celestial, Eternity, One Above All, All
CREATE TABLE IF NOT EXISTS meta_win_rates_rank (
    id                  SERIAL PRIMARY KEY,
    hero_name           VARCHAR(64) NOT NULL,
    rank_tier           VARCHAR(32) NOT NULL,
    game_mode           VARCHAR(16) NOT NULL,        -- 'competitive' or 'quickplay'
    win_rate            DECIMAL(5,2),
    pick_rate           DECIMAL(5,2),
    recorded_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, rank_tier, game_mode)
);

-- Public meta: hero win rates per map per rank
-- SOURCE: counterwatch.gg/stats/marvel-rivals/maps (scraped daily)
-- Enables: "Storm has 58% win rate on Yggdrasil at Gold rank (community)"
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

-- Map ID to name resolution cache (from /api/v1/maps, refreshed rarely)
CREATE TABLE IF NOT EXISTS map_cache (
    map_id              INT PRIMARY KEY,
    map_name            VARCHAR(128) NOT NULL,
    cached_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Logs each recommendation session for future analysis
CREATE TABLE IF NOT EXISTS recommendation_log (
    id                  SERIAL PRIMARY KEY,
    player_username     VARCHAR(64),
    map_name            VARCHAR(128),
    enemy_uids          BIGINT[],
    enemy_usernames     TEXT[],
    detected_via        VARCHAR(16) CHECK (detected_via IN ('manual', 'ocr')),
    llm_prompt          TEXT,
    llm_response        TEXT,
    recommended_heroes  TEXT[],
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_matches_player     ON user_matches (player_username);
CREATE INDEX idx_user_matches_player_uid ON user_matches (player_uid);
CREATE INDEX idx_user_matches_hero       ON user_matches (hero_played);
CREATE INDEX idx_user_matches_map        ON user_matches (map_name);
CREATE INDEX idx_user_matches_result     ON user_matches (result);
CREATE INDEX idx_enemy_profiles_uid      ON enemy_profiles (player_uid);
CREATE INDEX idx_meta_rank_hero          ON meta_win_rates_rank (hero_name, rank_tier);
CREATE INDEX idx_meta_map_hero           ON meta_win_rates_map (hero_name, map_name, rank_tier);
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
DATABASE_URL=postgresql://user:password@localhost:5432/rivals_db

# OCR Settings
SCREEN_RESOLUTION=1920x1080    # Used to select correct region presets
OCR_CONFIDENCE_THRESHOLD=0.6   # Minimum EasyOCR confidence to accept a name
```

---

## Phase 1 — Core Data Pipeline (Weekend 1)

**Goal:** Given a username, pull their full match history and store it in PostgreSQL.

### Tasks

**1.1 — Project setup**
- [ ] Create repo `rivals-counter-pick` on GitHub (`samirali123`)
- [ ] Set up virtual environment: `python -m venv venv`
- [ ] Create `requirements.txt` with initial deps:
  ```
  httpx
  psycopg2-binary
  python-dotenv
  anthropic
  rich
  easyocr
  mss
  ```
- [ ] Create `.env` from `.env.example`, populate with API keys
- [ ] Initialize PostgreSQL DB locally, run `schema.sql`

**1.2 — API client (`api/rivals_client.py`)**
```python
# Key methods to implement:

async def get_match_history(username: str, limit: int = 50, season: str = None) -> list[dict]:
    # GET /api/v2/player/{username}/match-history
    # Returns list of matches with match_uid, hero_played, is_win, map_id, timestamp

async def get_match_detail(match_uid: str) -> dict:
    # GET /api/v1/match/{match_uid}
    # Returns full lobby: all 12 players with camp, nick_name, uid, heroes played
    # THIS is how you get enemy usernames and hero data

async def get_player_stats(uid: int, season: str = None) -> dict:
    # GET /api/v2/player/{uid}  — PREMIUM
    # Use UID not username (more reliable per docs)
    # Returns hero win/loss breakdown, rank, isPrivate flag

async def get_hero_global_stats(hero_name: str) -> dict:
    # GET /api/v1/heroes/hero/{hero_name}/stats
    # Returns matches, wins — compute win_rate = wins/matches

async def get_hero_details(hero_name: str) -> dict:
    # GET /api/v1/heroes/hero/{hero_name}
    # Returns role, abilities, team-ups — useful for LLM context

async def get_map_list() -> dict:
    # GET /api/v1/maps
    # Returns map_id → map_name mapping, cache at startup

def get_enemies_from_match(match_detail: dict, user_uid: int) -> list[dict]:
    # Helper: filter match_players where camp != user's camp
    # Returns list of {uid, nick_name, heroes_played}
```
- Handle rate limiting with exponential backoff
- Cache map ID → name mapping at startup (static data)
- Cache hero global stats per session (doesn't change mid-session)

**1.3 — DB layer (`db/queries.py`)**
```python
# Key functions to implement:
def upsert_user_match(conn, match: dict) -> None
def upsert_enemy_profile(conn, username: str, hero_data: dict) -> None
def get_user_hero_stats(conn, username: str) -> list[dict]
def get_user_hero_stats_by_map(conn, username: str, map_name: str) -> list[dict]
def get_enemy_weaknesses(conn, username: str) -> list[dict]
```

**1.4 — Ingestion script**
- Pull user matches from API
- For each match, extract enemy usernames from match data
- Upsert all matches to `user_matches`
- Queue enemy usernames for profile lookup
- Upsert enemy hero stats to `enemy_profiles`

**Deliverable:** Running `python main.py --user "YourUsername" --ingest` populates the DB with your match history and all encountered enemies' hero data.

---

## Phase 2 — Analysis + LLM Recommendation (Weekend 2–3)

**Goal:** Given a username + enemy comp, output a ranked list of hero picks with reasoning.

### Tasks

**2.1 — User signals (`analysis/user_signals.py`)**
```python
def get_hero_winrates(conn, username: str) -> dict:
    # Returns: {"Storm": {"games": 23, "wins": 15, "winrate": 0.65}, ...}

def get_hero_winrates_on_map(conn, username: str, map_name: str) -> dict:
    # Same structure, filtered to specific map

def classify_comp(enemy_heroes: list[str]) -> str:
    # Returns comp archetype: "dive", "poke", "sustain", "brawl", "mixed"
    # Rule-based: define which heroes belong to which archetype

def get_winrate_vs_archetype(conn, username: str, archetype: str) -> dict:
    # Cross-reference matches where enemy_comp matched archetype
```

**2.2 — Enemy signals (`analysis/enemy_signals.py`)**
```python
def get_enemy_weaknesses(conn, enemy_usernames: list[str]) -> dict:
    # For each enemy, return heroes they have worst win rate on
    # Returns: {"PlayerA": {"worst_heroes": ["Storm", "Spider-Man"], "best_heroes": [...]}}

def aggregate_enemy_vulnerabilities(weakness_map: dict) -> dict:
    # Across all enemies, find heroes that exploit the most players simultaneously
```

**2.3 — Meta signals (`analysis/meta_signals.py`)**
```python
def get_rank_winrates(conn, rank_tier: str, game_mode: str = 'competitive') -> dict:
    # Pull from meta_win_rates_rank
    # Returns: {"Storm": {"win_rate": 0.51, "pick_rate": 0.08}, ...}

def get_map_winrates(conn, map_name: str, rank_tier: str = 'All') -> dict:
    # Pull from meta_win_rates_map for this specific map + rank
    # Returns: {"Storm": 0.58, "Thor": 0.44, ...}

def compute_personal_vs_community_delta(personal: dict, community: dict) -> dict:
    # For each hero in both dicts, compute delta = personal_wr - community_wr
    # Positive delta = player outperforms community on this hero
    # Returns: {"Storm": {"personal": 0.68, "community": 0.51, "delta": +0.17}, ...}

def refresh_hotlist_cache(conn) -> None:
    # Scrape marvelrivals.com/heroes_data/ for all rank tiers
    # Upsert into meta_win_rates_rank
    # Run once per day via manual trigger or scheduler

def refresh_map_cache(conn) -> None:
    # Scrape counterwatch.gg/stats/marvel-rivals/maps for each map + rank tier
    # Upsert into meta_win_rates_map
    # Run once per day
```

**2.4 — Prompt builder (`llm/prompt_builder.py`)**

The prompt is structured to give the LLM three layers of signal for each candidate hero:

```python
def build_context(...) -> str:
    return f"""
You are a Marvel Rivals coach. Recommend the top 3 hero picks for this player.
For each pick give a 1-2 sentence reason grounded in the data below.

PLAYER: {username}
CURRENT RANK: {player_rank}
MAP: {map_name}
ENEMY COMP: {', '.join(enemy_heroes)}
COMP TYPE: {comp_archetype}   (e.g. dive-heavy, poke, sustain)

PLAYER'S TOP HEROES — personal win rate vs community win rate at {player_rank}:
(Format: Hero | Personal WR | Community WR | Delta | Games Played)
{format_hero_comparison(personal_vs_community)}
Note: heroes with <10 games marked [LOW SAMPLE] — treat with caution

PLAYER WIN RATE VS {comp_archetype.upper()} COMPS HISTORICALLY:
{format_archetype_winrates(archetype_winrates)}

ENEMY VULNERABILITIES (heroes each enemy loses most to):
{format_enemy_signals(enemy_signals)}

MAP WIN RATES ON {map_name} (community, {player_rank} rank):
{format_map_winrates(map_winrates)}

INSTRUCTIONS:
- Weight personal performance most heavily — a hero the player wins on beats a meta pick they struggle with
- Flag if a strong personal pick has a positive delta (they outperform community) — this is a skill edge
- If the player has low sample on their top options, lean more on community map data
- Consider how well the pick exploits enemy vulnerabilities

Respond in this exact format:
1. [Hero Name] — [Reason grounded in data]
2. [Hero Name] — [Reason grounded in data]
3. [Hero Name] — [Reason grounded in data]
"""
```

**2.5 — Recommender (`llm/recommender.py`)**
```python
def get_recommendation(prompt: str) -> str:
    # Call Anthropic API
    # Parse and return the ranked list
    # Also log full prompt + response to recommendation_log table
```

**Deliverable:** Running `python main.py --user "YourUsername" --map "Tokyo 2099" --enemies "p1,p2,p3,p4,p5"` prints a clean ranked pick recommendation to the terminal.

---

## Phase 3 — Computer Vision Layer (Weekend 3–4)

**Goal:** Auto-detect enemy player names from a screenshot of the lobby or loading screen.

### Tasks

**3.1 — Screen region calibration (`cv/regions.py`)**

Marvel Rivals shows enemy names in a predictable screen location during the loading screen. Define bounding boxes per resolution:

```python
REGIONS = {
    "1920x1080": {
        "enemy_names": [
            (960, 280, 1400, 320),   # Enemy slot 1 (x1, y1, x2, y2)
            (960, 330, 1400, 370),   # Enemy slot 2
            (960, 380, 1400, 420),   # Enemy slot 3
            (960, 430, 1400, 470),   # Enemy slot 4
            (960, 480, 1400, 520),   # Enemy slot 5
            (960, 530, 1400, 570),   # Enemy slot 6
        ],
        "map_name": (840, 150, 1080, 190)
    }
    # Add more resolutions as needed
}
```

> **NOTE:** These coordinates are placeholders. They must be calibrated by
> taking a screenshot of the actual loading screen and measuring pixel positions.
> Use `calibrate.py` (to be written) to click-identify regions interactively.

**3.2 — Screen capture (`cv/capture.py`)**
```python
import mss

def capture_region(region: tuple) -> np.ndarray:
    # Takes (x1, y1, x2, y2), returns numpy array
    with mss.mss() as sct:
        monitor = {"top": region[1], "left": region[0],
                   "width": region[2]-region[0], "height": region[3]-region[1]}
        screenshot = sct.grab(monitor)
        return np.array(screenshot)

def capture_all_enemy_regions(resolution: str) -> list[np.ndarray]:
    # Captures all 6 enemy name slots, returns list of images
```

**3.3 — OCR pipeline (`cv/ocr.py`)**
```python
import easyocr

reader = easyocr.Reader(['en'])

def extract_name_from_region(image: np.ndarray) -> str | None:
    # Preprocess: grayscale, contrast boost, threshold
    # Run EasyOCR
    # Filter by confidence threshold from settings
    # Return cleaned name string or None

def extract_all_enemy_names() -> list[str]:
    # Capture all regions → run OCR on each → return list of detected names
    # Filters out None results (empty slots, low confidence)
```

**3.4 — Preprocessing considerations**
Marvel Rivals uses stylized fonts on dynamic backgrounds. To improve OCR accuracy:
- Convert region to grayscale
- Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) — same technique family as your Bilimetrix shadow compensation work
- Threshold to isolate white/bright text
- Optionally upscale 2x before feeding to EasyOCR

**3.5 — Calibration tool (`calibrate.py`)**
A small standalone script:
- Takes a full screenshot
- Displays it with `PIL`
- User clicks on each enemy name region
- Outputs the bounding box coordinates to paste into `regions.py`

**Deliverable:** Running `python main.py --user "YourUsername" --cv` takes a screenshot, extracts enemy names automatically, and runs the full recommendation pipeline.

---

## Phase 4 — Polish + Resume Packaging (Weekend 5)

**Goal:** Make the project presentable for interviews and GitHub.

### Tasks

**4.1 — README.md**
- Project overview and demo GIF (record terminal session with `asciinema`)
- Architecture diagram (copy from this doc)
- Setup instructions
- Example output
- Tech stack section

**4.2 — Demo mode**
Add `--demo` flag that runs with pre-loaded fixture data (no API key needed):
```bash
python main.py --demo
```
This lets you show it off in interviews without needing live credentials.

**4.3 — Error handling hardening**
- API timeout/rate limit handling
- OCR no-detection fallback (prompt manual input)
- DB connection failure handling
- Missing player profile (private account) handling

**4.4 — Performance logging**
Log timing for each phase so you can discuss latency in interviews:
```
[INFO] OCR extraction: 1.2s
[INFO] API lookups (7 players): 3.4s
[INFO] Analysis computation: 0.1s
[INFO] LLM inference: 2.1s
[INFO] Total: 6.8s
```

---

## Resume Bullet Points (draft for when complete)

```
Marvel Rivals Counter-Pick Engine | Python, PostgreSQL, EasyOCR, Anthropic API
• Built a real-time hero recommendation CLI that detects enemy player names via
  OCR screen capture, queries player profiles from a third-party REST API, and
  aggregates personal win-rate patterns, enemy vulnerability data, and live meta
  statistics into a structured LLM prompt to generate ranked counter-pick suggestions.
• Designed a PostgreSQL schema tracking per-hero win rates across maps and
  comp archetypes, with composite indexes enabling sub-10ms query response
  for cross-filtering match history by hero, map, and result.
• Implemented an OCR preprocessing pipeline (grayscale, CLAHE, adaptive
  thresholding) to extract stylized in-game text from screen regions,
  achieving reliable name detection across variable background conditions.
```

---

## API Findings — Confirmed from Documentation

This section replaces the Open Questions table. All key architectural questions are now answered.

### Confirmed Endpoint Behaviors

**`GET /api/v2/player/{query}/match-history`** — Free tier
- Returns paginated match history for the queried player only
- Each match includes: `match_uid`, `map_id` (integer, NOT name), `hero_played`, `kills/deaths/assists`, `is_win`, `season`, `game_mode`, `match_time_stamp`
- Does NOT include enemy team data — only the queried player's row
- Supports query params: `season`, `game_mode`, `page`, `limit`, `timestamp`
- **Implication:** This endpoint alone is not enough. You must follow up with the match detail call to get enemies.

**`GET /api/v1/match/{match_uid}`** — Free tier — THE KEY ENDPOINT
- Returns ALL players in the match (all 12)
- Each player entry includes: `player_uid`, `nick_name`, `camp` (0 or 1 = team side), `cur_hero_id`, `is_win`, `kills`, `deaths`, `assists`, `player_heroes` (list of heroes played with time, stats per hero)
- **To find enemies:** filter `match_players` where `camp != user_camp`
- **This is how you get enemy usernames.** The match history gives you `match_uid`; this call resolves the full lobby.

**`GET /api/v2/player/{query}`** — **PREMIUM endpoint**
- Returns full player profile: rank per season, overall stats, hero breakdowns
- Has `isPrivate` flag — private accounts return limited data
- Username search is flagged as "not always reliable" in docs; UID search is preferred
- **Implication:** You get enemy UIDs for free from the match detail call — always use UID for this lookup, not username
- **Cost consideration:** Every enemy lookup costs a premium API call. 6 enemies = 6 calls per session. Factor this into API plan choice.

**`GET /api/v1/heroes/hero/{query}/stats`** — Free tier
- Returns global stats for a hero: `matches`, `wins`, `k/d/a`, `total_hero_damage`, `session_hit_rate`
- Win rate = `wins / matches` — compute this yourself, not returned directly
- This is your meta win rate source. No map-level breakdown available here — map win rates will have to come from your own accumulated DB data over time.

**`GET /api/v1/heroes/hero/{query}`** — Free tier
- Full hero details: role, attack type, abilities with full keybind/cooldown/damage data, team-up abilities, costumes
- Useful for the LLM context: feeding ability descriptions helps it reason about counters
- `isCollab: true` flags on abilities indicate team-up skills

**`GET /api/v1/heroes/hero/{query}/stats` — map_name field**
- Map data from match history returns `match_map_id` (integer like `1217`), not a string name
- Use `GET /api/v1/maps` or `GET /api/v1/maps/map/{query}` to resolve map IDs to names
- Cache this mapping at startup — it won't change often

---

### Revised Data Flow (replaces Phase 1.2 description)

```
Session start:
  1. GET /api/v2/player/{username}/match-history?limit=50
     → extract: match_uid[], user_camp_per_match{}

  2. For each match_uid (batch async):
     GET /api/v1/match/{match_uid}
     → extract: enemy_players = [p for p in match_players if p.camp != user_camp]
     → store: enemy nick_names, enemy UIDs, enemy heroes played, map_id

  3. Resolve map IDs → names via cached map table

  4. Upsert all to user_matches + enemy_profiles tables

Session runtime (when recommendation requested):
  5. For each enemy UID from OCR/manual input:
     GET /api/v2/player/{enemy_uid}  [PREMIUM]
     → extract: hero win rates across seasons
     → upsert to enemy_profiles

  6. For each candidate hero (top 10 by user win rate):
     GET /api/v1/heroes/hero/{name}/stats  [Free]
     → compute win_rate = wins/matches
     → upsert to meta_win_rates

  7. Run analysis layer → build LLM prompt → get recommendation
```

---

### Remaining Unknowns (validate with live API key)

| Question | Impact if wrong |
|---|---|
| Does `player_heroes` in match detail show hero for full match or just final hero? | If only final hero, we lose swap data — still acceptable |
| Are `player_uid` values stable across seasons? | If they change, UID-based lookups break |
| What does `isPrivate: true` return for hero stats? | May need graceful fallback for private enemy profiles |
| Does free tier rate limit per minute or per day? | Determines if async batch calls need throttling |
| Does match history include Quick Play or ranked only by default? | Filter param `game_mode` should handle this |

---

## Stretch Goals (Post-MVP)

- **Team synergy analysis:** Factor in team-up abilities between your pick and likely ally heroes
- **Draft order awareness:** If you're picking late, adjust for what the enemy will likely ban/adjust to
- **Patch tracking:** Detect when meta cache is stale based on patch date, auto-refresh
- **Discord bot wrapper:** Expose the CLI as a slash command so you can query mid-lobby from your phone
- **Win prediction:** After enough logged matches, train a simple logistic regression on comp matchups

---

*Document version 1.2 — Meta data sources confirmed. Dual personal/community comparison design added. Schema split into rank and map win rate tables.*
