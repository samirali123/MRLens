# MRLens — Marvel Rivals Pick Advisor
### Project Plan v3.0 — CV-First, Self-Building Personal Database

---

## Vision

A background tool that watches your screen as you play Marvel Rivals and builds a
personal performance database automatically — no manual input, no API dependency
for your own games.

> **"The longer you play, the smarter it gets."**

### What it does

1. **Watches character select** — detects the map, side (attack/defense), your hero
   hover, and your teammates' hero hovers in real time
2. **Confirms picks at loading screen** — locks in the final hero selections for you
   and all 5 allies
3. **Watches the end screen** — detects win or loss, writes the completed match row
   to your personal database automatically
4. **Recommends picks mid-lobby** — as your teammates hover heroes, it surfaces your
   best options given the map, side, and ally comp forming in real time

### Core philosophy

- **Personal data beats public meta.** "You win 71% on Star-Lord when Magneto is on
  your team" is more valuable than any tier list.
- **Zero manual input.** The CV layer reads your screen. You never type anything.
- **Grows with you.** Day one it uses community data as a fallback. After 50+ games
  it's running almost entirely on your own history.

No frontend. Runs as a background process. Output is a clean CLI printout triggered
automatically when character select opens.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BACKGROUND WATCHER                           │
│   python main.py --uid 1554228221 --watch                       │
│   Polls screen every 2s. State machine drives detection.        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CV / SCREEN LAYER                            │
│                                                                 │
│   STATE: idle → character_select → loading → in_game → end     │
│                                                                 │
│   character_select:                                             │
│     - Map name (top center of screen)                           │
│     - Side: Attack / Defense label                              │
│     - Your hero hover (your portrait region)                    │
│     - Ally hero hovers (5 teammate portrait regions)            │
│     → Triggers: real-time recommendation output                 │
│                                                                 │
│   loading:                                                      │
│     - Confirmed hero names for you + all 5 allies               │
│     → Stores: confirmed ally comp in session                    │
│                                                                 │
│   end_screen:                                                   │
│     - "VICTORY" or "DEFEAT" text detection                      │
│     → Writes: completed match row to DB                         │
│     → Increments: hero + ally + map + side win/loss counts      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                │
│   PostgreSQL — self-populating from CV, no API required         │
│                                                                 │
│   user_matches:        one row per game played                  │
│     hero_played        your confirmed hero                      │
│     map_name           detected map                             │
│     side               attack / defense                         │
│     ally_heroes[]      all 5 teammate heroes                    │
│     result             win / loss (from end screen)             │
│     played_at          timestamp                                │
│                                                                 │
│   hero_synergies:      team-up ability pairs (from API, static) │
│   meta_win_rates_rank: community WR by rank (scraped daily)     │
│   meta_win_rates_map:  community WR by map (scraped daily)      │
│   map_cache:           map_id → name                            │
│   recommendation_log:  every prompt + response logged           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS LAYER                               │
│                                                                 │
│   Personal signals (from user_matches — grows with each game):  │
│   - Win rate per hero overall                                   │
│   - Win rate per hero on this map                               │
│   - Win rate per hero on this map + side (attack/defense)       │
│   - Win rate per hero + ally pair                               │
│     e.g. "Star-Lord + Magneto: 71% (14 games)"                  │
│   - Win rate per hero + full ally comp archetype                │
│                                                                 │
│   Active synergy signals (from current lobby):                  │
│   - Which of my top heroes get a boost with these allies?       │
│   - Which hero activates a team-up ability with an ally?        │
│   - Which role is missing from the current ally comp?           │
│                                                                 │
│   Community fallback signals (meta tables):                     │
│   - Community WR on this map at your rank                       │
│   - Personal vs community delta (your skill edge per hero)      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM RECOMMENDATION                           │
│   Local Ollama (llama3.1:8b) — no API cost, runs offline       │
│   Structured prompt → top 3 picks with grounded reasoning       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLI OUTPUT                                   │
│   Printed automatically when character select is detected       │
│   Updates live as ally hovers change                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | Best CV/ML ecosystem |
| Screen polling | `mss` | Fast cross-platform screenshot, ~1ms capture |
| OCR | `EasyOCR` | Accurate on stylized game fonts |
| Image processing | `opencv-python` | CLAHE, thresholding, template matching |
| API client | `httpx` (async) | Async HTTP for meta scraping |
| Database | PostgreSQL + `psycopg2` | Local, fast, grows with you |
| LLM | Ollama `llama3.1:8b` | Free, local, no API key |
| CLI output | `rich` | Clean colored terminal output |
| Config | `python-dotenv` | Secrets management |

---

## File Structure

```
MRLens/
│
├── main.py                       # Entry point + background watcher loop
│
├── config/
│   └── settings.py               # Env loading, constants, validation
│
├── cv/
│   ├── watcher.py                # State machine: idle→select→loading→end
│   ├── capture.py                # Screen capture via mss
│   ├── ocr.py                    # EasyOCR pipeline, name/text extraction
│   ├── regions.py                # Bounding boxes per resolution
│   ├── state_detector.py         # Detects current game state from screen
│   └── result_detector.py        # Detects VICTORY / DEFEAT on end screen
│
├── api/
│   ├── rivals_client.py          # MarvelRivalsAPI (match history, hero data)
│   ├── hotlist_client.py         # Scraper: MR Hero Hot List
│   └── counterwatch_client.py    # Scraper: counterwatch.gg map win rates
│
├── db/
│   ├── connection.py             # PostgreSQL connection pool
│   ├── schema.sql                # Full schema
│   └── queries.py                # All read/write functions
│
├── analysis/
│   ├── user_signals.py           # Personal WR per hero, map, side
│   ├── ally_signals.py           # Pair win rates, synergy detection
│   └── meta_signals.py           # Community WR, personal vs meta delta
│
├── llm/
│   ├── prompt_builder.py         # Builds structured LLM prompt
│   └── recommender.py            # Calls Ollama, parses response
│
├── cli/
│   └── output.py                 # Rich-formatted terminal output
│
├── calibrate.py                  # Interactive tool to set screen regions
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
-- One row per game played — self-populating via CV
CREATE TABLE IF NOT EXISTS user_matches (
    id              SERIAL PRIMARY KEY,
    match_uid       VARCHAR(64) UNIQUE,       -- from API if ingested, null if CV-only
    player_username VARCHAR(64) NOT NULL,
    player_uid      BIGINT,
    hero_played     VARCHAR(64) NOT NULL,
    map_name        VARCHAR(128),
    map_id          INT,
    side            VARCHAR(8) CHECK (side IN ('attack', 'defense', 'unknown')),
    result          VARCHAR(8) NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
    ally_heroes     TEXT[],                   -- all 5 teammate heroes
    enemy_comp      TEXT[],                   -- enemy heroes (future use)
    kills           INT,
    deaths          INT,
    assists         INT,
    season          VARCHAR(16),
    game_mode_id    INT,
    played_at       TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    source          VARCHAR(8) DEFAULT 'cv'   -- 'cv' or 'api'
);

-- Team-up ability pairs (populated once from API, rarely changes)
CREATE TABLE IF NOT EXISTS hero_synergies (
    id           SERIAL PRIMARY KEY,
    hero_name    VARCHAR(64) NOT NULL,
    ally_hero    VARCHAR(64) NOT NULL,
    synergy_name VARCHAR(128),
    cached_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, ally_hero)
);

-- Community win rates by rank (scraped daily)
CREATE TABLE IF NOT EXISTS meta_win_rates_rank (
    id          SERIAL PRIMARY KEY,
    hero_name   VARCHAR(64) NOT NULL,
    rank_tier   VARCHAR(32) NOT NULL,
    game_mode   VARCHAR(16) NOT NULL,
    win_rate    DECIMAL(5,2),
    pick_rate   DECIMAL(5,2),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, rank_tier, game_mode)
);

-- Community win rates by map (scraped daily from counterwatch.gg)
CREATE TABLE IF NOT EXISTS meta_win_rates_map (
    id          SERIAL PRIMARY KEY,
    hero_name   VARCHAR(64) NOT NULL,
    map_name    VARCHAR(128) NOT NULL,
    rank_tier   VARCHAR(32) NOT NULL DEFAULT 'All',
    win_rate    DECIMAL(5,2),
    source      VARCHAR(32) DEFAULT 'counterwatch',
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, map_name, rank_tier)
);

-- Map ID → name cache
CREATE TABLE IF NOT EXISTS map_cache (
    map_id    INT PRIMARY KEY,
    map_name  VARCHAR(128) NOT NULL,
    map_type  VARCHAR(32),
    cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Every recommendation session logged
CREATE TABLE IF NOT EXISTS recommendation_log (
    id                 SERIAL PRIMARY KEY,
    player_username    VARCHAR(64),
    map_name           VARCHAR(128),
    side               VARCHAR(8),
    ally_heroes        TEXT[],
    detected_via       VARCHAR(16),
    llm_prompt         TEXT,
    llm_response       TEXT,
    recommended_heroes TEXT[],
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Enemy player profiles (Phase 4 — requires premium API)
CREATE TABLE IF NOT EXISTS enemy_profiles (
    id              SERIAL PRIMARY KEY,
    player_uid      BIGINT NOT NULL,
    player_username VARCHAR(64),
    hero_name       VARCHAR(64) NOT NULL,
    games_played    INT DEFAULT 0,
    wins            INT DEFAULT 0,
    losses          INT DEFAULT 0,
    win_rate        DECIMAL(5,2),
    season          VARCHAR(16),
    is_private      BOOLEAN DEFAULT FALSE,
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (player_uid, hero_name, season)
);
```

---

## Environment Variables

```bash
RIVALS_API_KEY=your_key_here
RIVALS_API_BASE_URL=https://marvelrivalsapi.com/api/v1

OLLAMA_MODEL=llama3.1:8b

DATABASE_URL=postgresql://user@localhost:5432/rivals_db

SCREEN_RESOLUTION=1920x1080
OCR_CONFIDENCE_THRESHOLD=0.6
```

---

## Phase 1 — Foundation ✅ Complete

- Repo live at github.com/samirali123/MRLens
- PostgreSQL running locally, full schema applied
- `db/connection.py`, `db/queries.py` — all read/write functions
- `api/rivals_client.py` — match history, hero data, ally extraction
- `analysis/user_signals.py` — personal WR per hero, map, side
- `analysis/ally_signals.py` — pair win rates, synergy detection
- `analysis/meta_signals.py` — community WR, personal vs meta delta
- `llm/recommender.py` — Ollama (llama3.1:8b) local inference
- `llm/prompt_builder.py` — structured map/side/ally/synergy prompt
- `cli/output.py` — Rich terminal output
- `config/settings.py` — env validation, lazy headers
- 9/9 tests passing

---

## Phase 2 — CV Background Watcher (Current)

**Goal:** Watch the screen continuously. Detect game state. Recommend picks in
character select. Write match results automatically on the end screen.

### 2.1 — Screen region calibration (`cv/regions.py`, `calibrate.py`)

Define pixel regions for:
- Map name text (top center, character select)
- Side indicator: "Attacking" / "Defending" label
- Your hero portrait (bottom center of character select)
- 5 ally hero portraits (left side of character select)
- "VICTORY" / "DEFEAT" banner (center of end screen)

Run `python calibrate.py` to click-identify regions interactively on a screenshot.

### 2.2 — Game state detector (`cv/state_detector.py`)

A lightweight classifier that looks at the current screenshot and returns one of:
```
idle | character_select | loading | in_game | end_screen
```

Detection strategy:
- `character_select` — look for the map name region being non-empty + hero portraits visible
- `loading` — detect the loading bar or black screen with hero names
- `end_screen` — template match for "VICTORY" or "DEFEAT" text
- `in_game` — everything else while a session is active
- `idle` — no game running / main menu

### 2.3 — Result detector (`cv/result_detector.py`)

Reads the end screen:
- OCR on the result banner region → "VICTORY" or "DEFEAT"
- Maps to `"win"` or `"loss"` in the DB

### 2.4 — Background watcher (`cv/watcher.py`)

```python
# Runs as: python main.py --uid 1554228221 --watch
# Polls every 2 seconds

state_machine:
  idle:
    → poll screen
    → if character_select detected: transition to character_select

  character_select:
    → detect map, side, your hover, ally hovers every 2s
    → on first detection: print recommendation to terminal
    → re-print if ally hovers change significantly
    → if loading detected: save confirmed picks, transition to loading

  loading:
    → detect confirmed hero names for you + allies
    → store session: {map, side, your_hero, ally_heroes}
    → transition to in_game

  in_game:
    → poll every 5s (lower frequency, just watching for end screen)
    → if end_screen detected: transition to end_screen

  end_screen:
    → detect VICTORY / DEFEAT
    → write match row to DB:
        hero_played, map_name, side, ally_heroes[], result, played_at, source='cv'
    → print: "Match recorded: [hero] on [map] ([side]) — [result]"
    → transition to idle
```

### 2.5 — OCR additions (`cv/ocr.py`)

New functions needed:
- `extract_map_name()` — map name region → string
- `extract_side()` — side indicator region → "attack" | "defense"
- `extract_all_ally_names()` — 5 ally portrait regions → list of hero names
- `extract_my_hero()` — your portrait region → hero name
- `extract_result()` — end screen region → "win" | "loss"

### Deliverable

`python main.py --uid 1554228221 --watch` runs silently in the background. Every
game you play is automatically logged. The database grows with no manual input.

---

## Phase 3 — Data Growth + Recommendation Quality

**Goal:** Let personal data accumulate and tune recommendation quality.

### 3.1 — Minimum sample thresholds

| Games on hero | Treatment |
|---|---|
| 0–2 | Excluded from personal data, community data only |
| 3–9 | Shown with [LOW SAMPLE] warning |
| 10+ | Full confidence, weighted heavily |
| 3+ with a specific ally | Pair synergy qualifies for recommendation |

### 3.2 — Community meta scraping

Implement `api/hotlist_client.py` and `api/counterwatch_client.py`:
- Scrape hero win rates by rank from marvelrivals.com/heroes_data/
- Scrape map-specific win rates from counterwatch.gg
- Refresh daily, upsert into `meta_win_rates_rank` and `meta_win_rates_map`
- Used as fallback when personal data is thin

### 3.3 — Hero synergy table population

Call `/api/v1/heroes/hero/{name}` for all 40 heroes once:
- Extract `isCollab: true` abilities → which heroes activate team-ups together
- Upsert into `hero_synergies` table
- Used by the recommendation prompt as a bonus signal

### 3.4 — Stats CLI commands

```bash
# Your overall hero win rates
python main.py --uid 1554228221 --stats

# Your win rates on a specific map
python main.py --uid 1554228221 --stats --map "Tokyo 2099"

# Your synergy data for a specific hero
python main.py --uid 1554228221 --synergies "Star-Lord"

# All your hero pair win rates ranked
python main.py --uid 1554228221 --pairs
```

---

## Phase 4 — Enemy Analysis (Deferred)

Requires premium API access (`/api/v2/player/{uid}` — 1 call per enemy, 6/session).

Adds: which heroes each enemy player loses to most, cross-enemy vulnerability
aggregation. Deferred until API budget and tier are confirmed.

---

## Phase 5 — Polish

- `--demo` flag with fixture data (no keys needed, for showing off)
- README demo GIF via `asciinema`
- Performance timing logs
- Error handling: OCR miss → prompt manual input fallback

---

## CLI Reference

```bash
# Background watcher (main use case — runs forever)
python main.py --uid 1554228221 --watch

# Manual recommendation
python main.py --uid 1554228221 --map "Tokyo 2099" --side attack --allies "Thor,Magneto,Luna Snow,Hawkeye"

# One-time API ingest (historical matches, optional)
python main.py --uid 1554228221 --ingest

# Stats and synergy explorer
python main.py --uid 1554228221 --stats
python main.py --uid 1554228221 --synergies "Star-Lord"
python main.py --uid 1554228221 --pairs
```

---

## Key Metrics (what "smarter over time" looks like)

| Games played | Data available |
|---|---|
| 0 | Community meta only |
| 10 | Personal overall WR per hero unlocks |
| 30 | Map-specific WR starts forming |
| 50 | Map + side WR reliable for top heroes |
| 100+ | Ally pair synergies meaningful across most heroes |
| 200+ | Full personal model — community data mostly just confirmation |

---

## Resume Bullet Points (draft)

```
MRLens — Marvel Rivals Pick Advisor | Python, PostgreSQL, EasyOCR, OpenCV, Ollama
• Built a background CV tool that watches the game screen in real time, detects
  character select state, reads map/side/ally hero hovers via OCR, and recommends
  optimal picks using a locally-running LLM (llama3.1:8b via Ollama) — zero manual
  input required during gameplay.
• Self-building personal database: detects win/loss on the end screen and writes
  match rows automatically, accumulating per-hero win rates broken down by map,
  attack/defense side, and ally hero pairing — growing more accurate with each game.
• Designed PostgreSQL schema and query layer for sub-10ms cross-filtering of
  match history by hero, map, side, and ally composition using GIN indexes on
  array columns.
```

---

*Plan v3.0 — CV-first self-building database. Background watcher replaces manual
input. API used only for historical ingest and meta scraping.*
