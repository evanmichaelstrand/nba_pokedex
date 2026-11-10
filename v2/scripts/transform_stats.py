"""Turn raw NBA player stats into Pokémon-style base stats for one season.

Input:  data/raw/nba_player_stats_<compact>.csv (fetch_nba_data.py), data/raw/pokemon_stats.csv
Output: data/processed/nba_pokemon_stats_<compact>.csv  - the six base stats per qualified player
        data/processed/nba_input_scores_<compact>.csv   - each input's capped z-score and each
                                                          composite's percentile, for explaining results

Method (docs/stat_plan.md, "Standardization"):
  1. keep players with MIN_MINUTES+ total minutes
  2. per-36 rates for counting stats in PER36; optional log1p for stats in LOG
  3. z-score each input over qualified players, flip the sign where lower is better, cap at +/-Z_CAP
  4. composite = weighted average of its inputs' z-scores, re-weighted over the inputs a player has
  5. rank each composite (percentile) and take the Pokémon stat value at that percentile
"""
import argparse
import os

import numpy as np
import pandas as pd

from season_utils import season_to_compact

DEFAULT_SEASON = "2025-26"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

MIN_MINUTES = 500
Z_CAP = 3.0
STAT_MIN, STAT_MAX = 20, 150  # clip for mapped Pokémon stats (as v1)
INCLUDE_MEGAS = True  # Pokémon distribution includes Mega forms

STATS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]

# Pokémon stat -> {input column: weight}. Weights are relative within a composite.
COMPOSITES = {
    "hp": {"total_min": 2, "gp": 1},
    "attack": {"ppg": 45, "fg2_pct": 45, "dunks": 10},
    "defense": {"interior_def_fg_pct": 40, "dreb": 20, "blk": 20, "contested_shots": 20},
    "sp_attack": {"fg3m": 40, "net_off_rating": 20, "ast_minus_tov": 40},
    "sp_defense": {"net_def_rating": 30, "stl": 15, "deflections": 15, "charges_drawn": 10, "matchup_fg_pct_vs_guards": 30},
    "speed": {"oreb": 15, "loose_balls_recovered": 15, "transition_pts": 35, "drib_per_touch": 35},
}

# Lower is better: the z-score's sign is flipped
INVERT = {"interior_def_fg_pct", "net_def_rating", "matchup_fg_pct_vs_guards"}

# Season totals converted to per-36-minute rates, so playing time (HP's job) isn't counted twice
PER36 = {"dunks", "dreb", "blk", "contested_shots", "fg3m", "ast_minus_tov", "stl", "deflections",
         "charges_drawn", "oreb", "loose_balls_recovered", "transition_pts"}

# Per-game stats that the --per36 variant converts to per-36 (via season totals = per game x games).
# HP's inputs (total minutes, games) stay as totals in both variants.
PER_GAME_TO_PER36 = {"ppg"}

# Opt-in log1p transforms, each with its reason recorded in docs/stat_plan.md. None by default.
LOG = set()

# Percentages shrunk toward the league average by sample size: stat -> (attempts column, k).
# k is the stabilization point (docs/stat_plan.md, "Minimum samples"): at k attempts a value is pulled
# halfway to the league average. Shrunk values are z-scored against the unshrunk mean and SD, so a
# noisy input keeps a narrower spread (less pull on its composite) instead of being stretched back out.
SHRINK = {"matchup_fg_pct_vs_guards": ("matchup_fga_vs_guards", 850)}


def zscore(s, ref=None):
    """z-score of s, using ref's mean and SD when given."""
    ref = s if ref is None else ref
    sd = ref.std()
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - ref.mean()) / sd


def shrink(pct, attempts, k):
    """Pull each percentage toward the league average: (made + k * avg) / (attempts + k)."""
    made = pct * attempts
    has = pct.notna()
    league = made[has].sum() / attempts[has].sum()
    return (made + k * league) / (attempts + k)


def input_scores(nba, per36_variant=False):
    """Capped z-score for every input column used by a composite."""
    scores = pd.DataFrame(index=nba.index)
    for col in sorted({c for weights in COMPOSITES.values() for c in weights}):
        s = nba[col].astype(float)
        if s.isna().all():
            print(f"  {col}: no data this season; left out of its composite")
        if col in PER36:
            s = s / nba.total_min * 36
        elif per36_variant and col in PER_GAME_TO_PER36:
            s = s * nba.gp / nba.total_min * 36
        if col in LOG:
            s = np.log1p(s.clip(lower=0))
        if col in SHRINK:
            attempts_col, k = SHRINK[col]
            z = zscore(shrink(s, nba[attempts_col].astype(float), k), ref=s)
        else:
            z = zscore(s)
        if col in INVERT:
            z = -z
        scores[col] = z.clip(-Z_CAP, Z_CAP)
    return scores


def composite(scores, weights):
    """Weighted average over the inputs each player has (nulls re-weighted away)."""
    cols = list(weights)
    w = pd.Series(weights, dtype=float)
    present = scores[cols].notna()
    total = scores[cols].fillna(0).mul(w).sum(axis=1)
    weight_used = present.mul(w).sum(axis=1)
    return (total / weight_used).where(weight_used > 0)


def percentile_map(percentiles, poke_values):
    """Pokémon stat value at each NBA percentile, clipped to [STAT_MIN, STAT_MAX]."""
    mapped = np.percentile(poke_values, percentiles * 100)
    return np.clip(mapped, STAT_MIN, STAT_MAX)


def main(season=DEFAULT_SEASON, per36=False):
    compact = season_to_compact(season)
    nba = pd.read_csv(os.path.join(RAW_DIR, f"nba_player_stats_{compact}.csv"))
    poke = pd.read_csv(os.path.join(RAW_DIR, "pokemon_stats.csv"))
    if not INCLUDE_MEGAS:
        poke = poke[poke.is_default_form]

    nba = nba[nba.total_min >= MIN_MINUTES].reset_index(drop=True)
    print(f"{len(nba)} players with {MIN_MINUTES}+ minutes; Pokémon distribution from {len(poke)} Pokémon")

    if per36:
        print(f"Per-36 variant: {', '.join(sorted(PER_GAME_TO_PER36))} converted from per game to per 36 minutes")
    scores = input_scores(nba, per36_variant=per36)

    out = nba[["PLAYER_ID", "name", "team", "position"]].copy()
    explain = nba[["PLAYER_ID", "name", "team"]].copy()
    for stat, weights in COMPOSITES.items():
        comp = composite(scores, weights)
        missing = comp.isna().sum()
        if missing:
            print(f"  {stat}: {missing} players have no inputs; placed at the median")
            comp = comp.fillna(comp.median() if comp.notna().any() else 0)
        pct = comp.rank(pct=True)
        out[stat] = percentile_map(pct.to_numpy(), poke[stat].to_numpy()).round().astype(int)
        explain[f"{stat}_composite"] = comp.round(4)
        explain[f"{stat}_pctile"] = (pct * 100).round(1)
        partial = scores[list(weights)].isna().any(axis=1).sum()
        if partial:
            print(f"  {stat}: {partial} players missing at least one input (re-weighted)")
    out["base_stat_total"] = out[STATS].sum(axis=1)

    for col in scores.columns:
        explain[f"z_{col}"] = scores[col].round(3)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    variant = "per36_" if per36 else ""
    stats_path = os.path.join(OUTPUT_DIR, f"nba_pokemon_stats_{variant}{compact}.csv")
    explain_path = os.path.join(OUTPUT_DIR, f"nba_input_scores_{variant}{compact}.csv")
    out.to_csv(stats_path, index=False)
    explain.to_csv(explain_path, index=False)
    print(f"\nSaved {len(out)} players to {stats_path}")
    print(f"Saved input z-scores and composite percentiles to {explain_path}")
    print(out.sort_values("base_stat_total", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transform NBA stats into Pokémon-style base stats.")
    parser.add_argument("--season", default=DEFAULT_SEASON, help="Season in form 'YYYY-YY' (e.g. 2025-26)")
    parser.add_argument("--per36", action="store_true",
                        help="Variant: per-game stats (PPG) as per 36 minutes; writes *_per36_<season>.csv files")
    args = parser.parse_args()
    main(args.season, args.per36)
