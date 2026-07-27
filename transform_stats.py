import os
import numpy as np
import pandas as pd

INPUT_NBA  = os.path.join("data", "raw", "nba_player_stats.csv")
INPUT_POKE = os.path.join("data", "raw", "pokemon_stats.csv")
OUTPUT_DIR = os.path.join("data", "processed")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "nba_pokemon_stats.csv")

STAT_MIN = 20
STAT_MAX = 200


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


def main():
    nba  = pd.read_csv(INPUT_NBA)
    poke = pd.read_csv(INPUT_POKE)

    # Filter players with fewer than 300 total minutes
    nba = nba[nba["gp"] * nba["min_pg"] >= 300].reset_index(drop=True)
    print(f"{len(nba)} players after 300-minute filter")

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
    n["ppg"]                  = min_max_norm(nba["ppg"])
    n["ts_pct"]               = min_max_norm(nba["ts_pct"])
    n["on_ball_def_fg_pct"]   = 1 - min_max_norm(nba["on_ball_def_fg_pct"])  # inverted: lower opp FG% = better
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
    n["stl_per_min"]              = min_max_norm(nba["stl"]                   / nba["min_pg"])

    # --- Derive composite stats ---
    hp         = n["height"] * n["weight"]
    attack     = n["ppg"] * n["ts_pct"]
    defense    = 0.50 * n["on_ball_def_fg_pct"] + 0.20 * n["blk"] + 0.30 * n["reb"]
    sp_attack  = 0.50 * n["ast_minus_tov"]       + 0.50 * n["net_off_rating"]
    sp_defense = 0.20 * n["stl"]                 + 0.80 * n["net_def_rating"] 
    speed      = 0.3 * n["charges_per_min"] + 0.3 * n["loose_balls_per_min"] + 0.10 * n["box_outs_per_min"] + 0.3 * n["stl_per_min"]

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
    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(out)} players to {OUTPUT_FILE}")
    print(out.head(10).to_string())


if __name__ == "__main__":
    main()
