---
name: check-stat-feasibility
description: Check whether an NBA stat (or a stat matching a description, e.g. "jump height", "change of direction", "how often a player cuts") can be pulled via nba_api, by searching nba_api source and verifying with a live call. Use whenever the user asks if a stat is available, which endpoint has it, or what stats exist for a trait — and record results in the stat catalog.
---

# Check stat feasibility

Answer "can we get stat X?" with evidence from a live call, not from nba_api docs alone. The docs are auto-generated and incomplete (e.g. no column list for `SynergyPlayTypes`, no mention of `DunkScoreLeaders` breaking with defaults).

## 0. Check the catalog first

Read `v2/docs/stat_catalog.md`. If the stat is already there with status and coverage, answer from it. Re-verify only if the user needs a season the entry doesn't cover, or the entry is old enough that the API may have changed.

## 1. Find candidates in nba_api source

The source is kept at `C:\Users\evanm\.cache\nba_api_src` (outside the repo). Refresh or create it with absolute paths only — never chain a `cd` with `git` fallbacks, which once ran `git sparse-checkout` inside this repo and hid every file:

```bash
D=/c/Users/evanm/.cache/nba_api_src
if [ -d "$D/.git" ]; then git -C "$D" pull -q --ff-only; else git clone -q --depth 1 https://github.com/swar/nba_api.git "$D"; fi
```

Search (with Grep, path `C:\Users\evanm\.cache\nba_api_src\src\nba_api\stats`):
- `endpoints/` (recursive — includes `endpoints/_expected_data/`): column names. Translate the description into likely column-name fragments (jump → `VERTICAL|LEAP|JUMP`, speed → `SPEED|SPRINT|DIST`, etc.) and grep case-insensitively; NBA uses both `UPPER_SNAKE` and `camelCase`.
- `library/parameters.py`: options for `PtMeasureType`, `PlayType`, `DefenseCategory`, `MeasureTypeDetailedDefense`, etc. Many stats live behind a parameter value, not a column name.
- An endpoint's `__init__` signature for required parameters and defaults (e.g. `SynergyPlayTypes` defaults to team-level data).

Prefer league-wide endpoints (`LeagueDash*`, `LeagueHustle*`, `SynergyPlayTypes`, `DunkScoreLeaders`) — one call per season for all players. Per-game/per-player/per-team endpoints (`BoxScore*`, `PlayerDash*`, `TeamPlayerOnOffSummary`) need many rate-limited calls; flag that cost.

## 2. Verify with a live call

Run from the repo root (the season is usually the latest completed one unless the user says otherwise):

```bash
python .claude/skills/check-stat-feasibility/probe.py <EndpointClass> --season 2025-26 --param key=value ... [--show colA,colB] [--top colA] [--raw-key KEY] [--out <scratchpad>/x.csv]
```

It prints the call made, result sets, row count, unique players, columns with null %, stats for `--show` columns, and sample rows. It falls back to raw JSON when nba_api fails to parse, and prints the API's error text or HTTP status when there's no data. Run `python .claude/skills/check-stat-feasibility/probe.py -h` for examples.

Check, and report:
- **Coverage**: rows / unique players vs. the player pool (≈570–590 players appear in a season; ≈380 have 500+ minutes). For a precise figure, `--out` to the scratchpad and merge on `PLAYER_ID` against a v1 raw stats CSV (`v1/data/raw/nba_player_stats_<compact>.csv`).
- **Nulls** in the columns that matter.
- **Completeness**: for event-level data, compare distinct games against a full season (1,230 regular-season games). Large responses are silently capped at 102,400 rows, and the cut is not cleanly by date (probe.py warns). Split by month with `date_from_nullable`/`date_to_nullable`. If two sources measure the same thing, cross-check per-player counts.
- **Sanity**: do the leaders (`--top`) look right to a basketball fan?
- **Seasons**: if history matters, probe one or two older seasons — many tracking feeds start in a specific year.
- **Sample size**: event-level data (dunks, play types) needs a minimum-count filter; say what a reasonable one is.

Space calls ~1s apart; stats.nba.com throttles bursts. A timeout or empty HTTP 500 can mean "no data for these params" — retry once before concluding.

## 3. Report

Lead with a verdict: **Available**, **Partial** (coverage gaps, workarounds, or proxy only), or **Not available**. Then: endpoint + exact parameters, relevant columns, measured coverage, quirks/workarounds, fetch cost (calls per season). For a descriptive request ("athleticism"), give a table grouped by trait and separate direct measurements from proxies. Say plainly when something isn't exposed by any endpoint.

## 4. Update the catalog

Add or update the entry in `v2/docs/stat_catalog.md` following its format, with the date verified and the season(s) tested. Record "not available" findings too, so they aren't re-investigated. Only mark something verified if a live call in this session confirmed it.
