import argparse
import os
import numpy as np
import pandas as pd

from season_utils import season_to_compact

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_POKE = os.path.join(PROJECT_ROOT, "data", "raw", "pokemon_stats.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

STAT_MIN = 20
STAT_MAX = 150


def min_max_norm(series):
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.0, index=series.index)
    return (series - mn) / (mx - mn)


def percentile_map(nba_series, poke_series):
    """Map each player's derived score to its percentile, then look up the
    equivalent Pokémon stat value at that percentile in the Pokémon distribution."""
    poke_vals = poke_series.dropna().values
    percentiles = nba_series.rank(pct=True)
    mapped = percentiles.apply(lambda p: np.percentile(poke_vals, p * 100))
    return mapped.clip(lower=STAT_MIN, upper=STAT_MAX)


def main(season="2025-26"):
    compact = season_to_compact(season)
    input_nba = os.path.join(PROJECT_ROOT, "data", "raw", f"nba_player_stats_{compact}.csv")
    output_file = os.path.join(OUTPUT_DIR, f"nba_pokemon_stats_{compact}.csv")
    output_norm_file = os.path.join(OUTPUT_DIR, f"nba_normalized_stats_{compact}.csv")

    nba  = pd.read_csv(input_nba)
    poke = pd.read_csv(INPUT_POKE)

    # Filter players with fewer than 500 total minutes
    nba = nba[nba["total_min"] >= 500].reset_index(drop=True)
    print(f"{len(nba)} players after 500-minute filter")

    # Fill any missing values with column median before normalizing
    stat_inputs = [
        "height", "weight", "ppg", "ts_pct", "on_ball_def_fg_pct",
        "blk", "reb", "ast", "tov", "net_off_rating",
        "stl", "net_def_rating", "charges_drawn", "loose_balls_recovered", "box_outs",
    ]
    for col in stat_inputs:
        nba[col] = nba[col].fillna(nba[col].median())

    # --- Pre-normalize each input factor ---
    n = pd.DataFrame(index=nba.index)
    n["height"]               = min_max_norm(nba["height"])
    n["weight"]               = min_max_norm(nba["weight"])
    n["min"]                  = min_max_norm(nba["total_min"])
    n["ppg"]                  = min_max_norm(nba["ppg"])
    n["ts_pct"]               = min_max_norm(nba["ts_pct"])
    n["fg2_pct"]              = min_max_norm(nba["fg2_pct"])
    n["fg3_pct"]              = min_max_norm(nba["fg3_pct"])
    n["fg2a"]              = min_max_norm(nba["fg2a"])
    n["fg3a"]              = min_max_norm(nba["fg3a"])
    n["on_ball_def_fg_pct"]   = 1 - min_max_norm(nba["on_ball_def_fg_pct"])  # inverted: lower opp FG% = better
    n["interior_def_fg_pct"]   = 1 - min_max_norm(nba["interior_def_fg_pct"])
    n["perimeter_def_fg_pct"]   = 1 - min_max_norm(nba["perimeter_def_fg_pct"])
    n["blk"]                  = min_max_norm(nba["blk"])
    n["reb"]                  = min_max_norm(nba["reb"])
    n["ast_minus_tov"]        = min_max_norm(nba["ast"] - nba["tov"])          # raw diff first, then normalize
    n["net_off_rating"]       = min_max_norm(nba["net_off_rating"])            # higher = better, no inversion
    n["stl"]                  = min_max_norm(nba["stl"])
    n["net_def_rating"]       = 1 - min_max_norm(nba["net_def_rating"])        # inverted: more negative on-off = better defender
    # Per-minute versions for speed (removes volume bias from playing time)
    n["charges_per_min"]          = min_max_norm(nba["charges_drawn"]        / nba["min_pg"])
    n["loose_balls_per_min"]      = min_max_norm(nba["loose_balls_recovered"] / nba["min_pg"])
    n["box_outs_per_min"]         = min_max_norm(nba["box_outs"]              / nba["min_pg"])
    n["charges"]          = min_max_norm(nba["charges_drawn"])
    n["loose_balls"]      = min_max_norm(nba["loose_balls_recovered"])
    n["box_outs"]         = min_max_norm(nba["box_outs"])
    n["stl_per_min"]              = min_max_norm(nba["stl"]                   / nba["min_pg"])
    # avg speed
    n["avg_speed"]                = min_max_norm(nba["avg_speed"])
    n["fg3m"]                     = min_max_norm(nba["fg3_pct"] * nba["fg3a"])

    # --- Derive composite stats ---
    hp         = n["min"] #n["height"] * n["weight"]
    attack     = 0.50 * n["ppg"] + 0.50 * n["fg2_pct"]
    defense    = 0.50 * n["interior_def_fg_pct"] + 0.20 * n["blk"] + 0.30 * n["reb"]
    sp_attack  = 0.33 * n["ast_minus_tov"]       + 0.34 * n["net_off_rating"] + 0.33 * n["fg3m"]
    sp_defense = 0.50 * n["perimeter_def_fg_pct"] + 0.30 * n["net_def_rating"] + 0.20 * n["stl"]         
    speed      = 0.3 * n["avg_speed"] + 0.3 * n["loose_balls"] + 0.3 * n["charges"] + 0.1 * n["box_outs"]
    #0.3 * n["charges_per_min"] + 0.3 * n["loose_balls_per_min"] + 0.10 * n["box_outs_per_min"] + 0.3 * n["stl_per_min"]

    # --- Post-map: percentile rank among NBA players → Pokémon stat distribution ---
    out = nba[["PLAYER_ID", "name", "team"]].copy()

    out["hp"]         = percentile_map(hp,         poke["hp"]).round().astype(int)
    out["attack"]     = percentile_map(attack,     poke["attack"]).round().astype(int)
    out["defense"]    = percentile_map(defense,    poke["defense"]).round().astype(int)
    out["sp_attack"]  = percentile_map(sp_attack,  poke["sp_attack"]).round().astype(int)
    out["sp_defense"] = percentile_map(sp_defense, poke["sp_defense"]).round().astype(int)
    out["speed"]      = percentile_map(speed,      poke["speed"]).round().astype(int)
    out["base_stat_total"] = out[["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]].sum(axis=1)

    # Normalized input factors (for interpretability)
    out["norm_height"]                = n["height"].round(4)
    out["norm_weight"]                = n["weight"].round(4)
    out["norm_ppg"]                   = n["ppg"].round(4)
    out["norm_ts_pct"]                = n["ts_pct"].round(4)
    out["norm_on_ball_def_fg_pct"]    = n["on_ball_def_fg_pct"].round(4)
    out["norm_blk"]                   = n["blk"].round(4)
    out["norm_reb"]                   = n["reb"].round(4)
    out["norm_ast_minus_tov"]         = n["ast_minus_tov"].round(4)
    out["norm_net_off_rating"]        = n["net_off_rating"].round(4)
    out["norm_stl"]                   = n["stl"].round(4)
    out["norm_net_def_rating"]        = n["net_def_rating"].round(4)
    out["norm_charges_per_min"]          = n["charges_per_min"].round(4)
    out["norm_loose_balls_per_min"]      = n["loose_balls_per_min"].round(4)
    out["norm_box_outs_per_min"]         = n["box_outs_per_min"].round(4)
    out["norm_stl_per_min"]              = n["stl_per_min"].round(4)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out.to_csv(output_file, index=False)
    print(f"Saved {len(out)} players to {output_file}")
    print(out.head(10).to_string())

    # --- Spreadsheet of percentile ranks for each input that feeds a composite stat ---
    def pctile(series):
        return (series.rank(pct=True) * 100).round(1)

    norm_out = nba[["name", "team"]].copy()
    norm_out["pctile_min"]                  = pctile(n["min"])                  # hp
    norm_out["pctile_ppg"]                  = pctile(n["ppg"])                  # attack
    norm_out["pctile_fg2_pct"]              = pctile(n["fg2_pct"])              # attack
    norm_out["pctile_interior_def_fg_pct"]  = pctile(n["interior_def_fg_pct"])  # defense
    norm_out["pctile_blk"]                  = pctile(n["blk"])                  # defense
    norm_out["pctile_reb"]                  = pctile(n["reb"])                  # defense
    norm_out["pctile_ast_minus_tov"]        = pctile(n["ast_minus_tov"])        # sp_attack
    norm_out["pctile_net_off_rating"]       = pctile(n["net_off_rating"])       # sp_attack
    norm_out["pctile_fg3m"]                 = pctile(n["fg3m"])                 # sp_attack
    norm_out["pctile_perimeter_def_fg_pct"] = pctile(n["perimeter_def_fg_pct"]) # sp_defense
    norm_out["pctile_net_def_rating"]       = pctile(n["net_def_rating"])       # sp_defense
    norm_out["pctile_stl"]                  = pctile(n["stl"])                  # sp_defense
    norm_out["pctile_avg_speed"]            = pctile(n["avg_speed"])            # speed
    norm_out["pctile_loose_balls"]          = pctile(n["loose_balls"])          # speed
    norm_out["pctile_charges"]              = pctile(n["charges"])              # speed
    norm_out["pctile_box_outs"]             = pctile(n["box_outs"])             # speed

    norm_out.to_csv(output_norm_file, index=False)
    print(f"\nSaved {len(norm_out)} players' normalized stats to {output_norm_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transform NBA stats into Pokemon-style base stats.")
    parser.add_argument("--season", default="2025-26", help="Season in form 'YYYY-YY' (e.g. 2025-26)")
    args = parser.parse_args()
    main(args.season)
