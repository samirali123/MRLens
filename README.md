# MRLens

A terminal-based hero recommendation engine for Marvel Rivals. Answers one question mid-lobby:

> **"Given this map, this side, and these teammates — what should I play?"**

---

## How it works

MRLens pulls your personal match history and builds a local profile of your win rates per hero, per map, and per side (attack vs defense). When you're in a lobby, it takes that context — map, side, your teammates' heroes — and feeds it into Claude to generate ranked pick recommendations with plain-English reasoning.

**Signals used, in priority order:**

1. Your win rate on this hero on this specific map and side
2. Team-up synergies with your current allies
3. Role coverage gaps (missing healer, missing tank, etc.)
4. Your overall win rate per hero
5. Community meta win rates at your rank on this map

---

## Usage

**Ingest your match history first (run once, then periodically):**
```bash
python main.py --user "YourUsername" --ingest
```

**Get a recommendation (manual mode):**
```bash
python main.py --user "YourUsername" \
  --map "Tokyo 2099" \
  --side attack \
  --allies "Thor,Loki,Luna Snow,Hawkeye" \
  --rank Gold
```

**Get a recommendation (auto-detect via screen capture):**
```bash
python main.py --user "YourUsername" --cv
```

**View your hero stats:**
```bash
python main.py --user "YourUsername" --stats
```

---

## Example output

```
╭─────────────────────────────────────────────╮
│       Marvel Rivals Counter-Pick Engine      │
│  Player:  SamirAli                           │
│  Map:     Tokyo 2099  (Escort)               │
│  Side:    Attack                             │
│  Allies:  Thor, Loki, Luna Snow, Hawkeye     │
╰─────────────────────────────────────────────╯

╭─────────────── Recommended Picks ───────────╮
│ 1. Captain America — Your best map+side hero │
│    (71% WR on Tokyo 2099 attack, 14 games).  │
│    Also activates Thunderstrike team-up with │
│    Thor already on your team.                │
│                                              │
│ 2. Storm — Strong community WR on this map  │
│    (58% at Gold). Your personal WR is 64%   │
│    (+6% vs community). Good escort pusher.  │
│                                              │
│ 3. Mantis — Team has no second healer.       │
│    You win 61% on her overall (22 games)    │
│    and she pairs well with Luna Snow.        │
╰─────────────────────────────────────────────╯

[INFO] API lookups:           2.1s
[INFO] Analysis computation:  0.1s
[INFO] LLM inference:         2.3s
[INFO] Total:                 4.5s
```

---

## Setup

**1. Clone and create a virtual environment:**
```bash
git clone https://github.com/samirali123/MRLens.git
cd MRLens
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys:
- `RIVALS_API_KEY` — from [marvelrivalsapi.com](https://marvelrivalsapi.com)
- `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com)
- `DATABASE_URL` — PostgreSQL connection string

**3. Set up PostgreSQL:**
```bash
createdb rivals_db
psql rivals_db -f db/schema.sql
```

**4. Ingest your match history:**
```bash
python main.py --user "YourUsername" --ingest
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Screen capture | `mss` |
| OCR | `EasyOCR` |
| API client | `httpx` (async) |
| Database | PostgreSQL + `psycopg2` |
| LLM | Anthropic API (Claude) |
| CLI output | `rich` |
| Config | `python-dotenv` |

---

## Project status

| Phase | Status |
|---|---|
| Phase 1 — Core data pipeline | In progress |
| Phase 2 — Analysis + LLM recommendation | In progress |
| Phase 3 — CV / OCR auto-detection | Planned |
| Phase 4 — Enemy player analysis | Deferred |
| Phase 5 — Polish + demo mode | Planned |
