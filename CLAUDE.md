# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

NBA Pokédex: maps NBA players to Pokémon by converting each player's real stats into a Pokémon-style base stat line (HP/Atk/Def/SpA/SpD/Spe) and finding the nearest Pokémon. Output CSVs are used for social content, so match results are the product.

## Versions

Each algorithm version is a fully self-contained folder (its own code, `requirements.txt`, README and `data/`). Versions do not import from or share files with each other.

- `v1/` — the original pipeline. **Frozen**: treat as historical reference and do not modify unless explicitly asked.
- `v2/` — new implementation, being written from scratch. v1 is only a loose reference; do not copy v1's structure or code into v2 by default.

When adding a version, create a new sibling folder rather than editing an existing one. Update this file as v2 takes shape.

## v2

In progress: data fetching exists; transform and matching do not yet.

```bash
pip install -r v2/requirements.txt
python v2/scripts/fetch_nba_data.py --season 2025-26   # ~45 calls, ~2 min -> v2/data/raw/nba_player_stats_<compact>.csv
python v2/scripts/fetch_pokemon_data.py [--forms none|mega|all]   # ~1,100 calls, several minutes -> v2/data/raw/pokemon_stats.csv
```

- `v2/docs/stat_plan.md` is the source of truth for which NBA stats feed each Pokémon stat, per-stat minimum samples, and the first season each stat exists. `fetch_nba_data.py` mirrors it in `FIRST_SEASON` and `MIN_SAMPLES`; keep them in sync.
- The NBA fetch keeps all players (the 500-minute filter belongs in the transform step) but applies minimum samples: below the minimum, that stat is null. Sources that don't exist yet for an older season are skipped and their columns left null.
- Traded players: on/off ratings are combined across teams weighted by minutes, and `team` is the team with the most minutes (falls back to last team before 2007-08, when on/off data starts). v1 got this wrong.
- Dunks come from the league-wide shot chart fetched month by month, because a single call is silently capped at 102,400 rows.
- Pokémon species are discovered from PokéAPI's generation list (new generations appear automatically); Mega forms are included by default with PokéAPI's own ids (10000+). The script exits non-zero if any Pokémon fails after retries.

## NBA stat availability

`v2/docs/stat_catalog.md` records which stats nba_api can actually provide (endpoint, params, columns, measured coverage, quirks). For any "is stat X available?" question, use the `check-stat-feasibility` skill (`.claude/skills/check-stat-feasibility/`), which checks the catalog, searches nba_api source kept at `C:\Users\evanm\.cache\nba_api_src`, verifies with a live call via its `probe.py`, and updates the catalog. Don't rely on the nba_api docs alone; they omit columns and known breakages.

## v1

Run from the repo root (scripts resolve `data/` relative to their own folder, so the working directory doesn't matter):

```bash
pip install -r v1/requirements.txt              # nba_api, pandas, numpy, requests (Python 3.9+)
python v1/master.py 2025-26                     # full pipeline (season arg required)
python v1/scripts/transform_stats.py --season 2025-26   # single stage
```

No tests, linter, or build step. Iterating on formulas only needs stages 3–4, which run in seconds off cached raw CSVs. The fetch stages are slow: ~1025 PokéAPI calls (0.2s delay each) and ~40 stats.nba.com calls (1s delay, one `TeamPlayerOnOffSummary` per team).

Four stages that communicate only through CSVs in `v1/data/`:

1. `fetch_pokemon_data.py` → `raw/pokemon_stats.csv` (national dex 1–1025, no alternate forms)
2. `fetch_nba_data.py` → `raw/nba_player_stats_<compact>.csv` — left-merges ~10 `nba_api` endpoints on `PLAYER_ID`; uses a module-level `SEASON` global that `main(season)` overwrites
3. `transform_stats.py` → `processed/nba_pokemon_stats_<compact>.csv` + `nba_normalized_stats_<compact>.csv` (per-input percentile ranks)
4. `match_pokemon.py` → `processed/nba_pokemon_matches_{unique,true}_<compact>.csv`

`<compact>` is from `season_utils.season_to_compact` (`"2025-26"` → `"2526"`). Scripts import `season_utils` as a sibling module, so run them by path, not with `-m`.

Algorithm summary (full stat-to-input table in `v1/README.md`):
- Filter to `total_min >= 500`; min-max normalize each input across that pool, inverting "lower is better" inputs (opponent FG%, `net_def_rating`).
- Each Pokémon stat = weighted sum of normalized inputs, then percentile-mapped onto the real Pokémon distribution for that stat, clipped to [20, 150]. Outputs reflect rank among NBA players, not absolute values.
- Matching: Euclidean distance over 6 stats ÷ the pair's average base stat total. "Unique" = greedy global assignment (best pairs first, each Pokémon used once); "true" = per-player argmin, repeats allowed.

Files in `v1/data/` without a season suffix (e.g. `nba_pokemon_matches.csv`, `nba_pokemon_stats_gt500.csv`, `nba_player_stats_2024-25.csv`) are legacy outputs not produced by current v1 code.
