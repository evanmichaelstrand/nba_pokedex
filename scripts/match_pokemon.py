import argparse
import os
import numpy as np
import pandas as pd

from season_utils import season_to_compact

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_POKE = os.path.join(PROJECT_ROOT, "data", "raw", "pokemon_stats.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

STATS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]


def main(season="2024-25"):
    compact = season_to_compact(season)
    input_nba = os.path.join(PROJECT_ROOT, "data", "processed", f"nba_pokemon_stats_{compact}.csv")
    output_file_unique = os.path.join(OUTPUT_DIR, f"nba_pokemon_matches_unique_{compact}.csv")
    output_file_true   = os.path.join(OUTPUT_DIR, f"nba_pokemon_matches_true_{compact}.csv")

    nba  = pd.read_csv(input_nba)
    poke = pd.read_csv(INPUT_POKE)

    poke["base_stat_total"] = poke[STATS].sum(axis=1)

    # Vectorized Euclidean distance: (n_players, n_pokemon)
    nba_vals  = nba[STATS].values
    poke_vals = poke[STATS].values
    raw_dist  = np.sqrt(((nba_vals[:, np.newaxis, :] - poke_vals[np.newaxis, :, :]) ** 2).sum(axis=2))

    # Normalize by each pair's average base stat total, so high-BST and low-BST
    # pairs are compared proportionally rather than by raw point differences
    nba_bst  = nba["base_stat_total"].values
    poke_bst = poke["base_stat_total"].values
    avg_bst  = (nba_bst[:, np.newaxis] + poke_bst[np.newaxis, :]) / 2
    norm_diff = raw_dist / avg_bst

    n_players, n_pokemon = norm_diff.shape

    def build_output(best_idx):
        matched = poke.iloc[best_idx].reset_index(drop=True)

        out = nba[["PLAYER_ID", "name", "team"] + STATS + ["base_stat_total"]].copy()

        out["pokemon_id"]              = matched["id"].values
        out["pokemon_name"]            = matched["name"].values
        out["pokemon_type1"]           = matched["type1"].values
        out["pokemon_type2"]           = matched["type2"].values
        out["pokemon_hp"]              = matched["hp"].values
        out["pokemon_attack"]          = matched["attack"].values
        out["pokemon_defense"]         = matched["defense"].values
        out["pokemon_sp_attack"]       = matched["sp_attack"].values
        out["pokemon_sp_defense"]      = matched["sp_defense"].values
        out["pokemon_speed"]           = matched["speed"].values
        out["pokemon_base_stat_total"] = matched["base_stat_total"].values

        out["total_stat_difference"] = norm_diff[np.arange(len(nba)), best_idx].round(4)
        out["match_quality_percentile"] = (
            out["total_stat_difference"].rank(ascending=False, pct=True) * 100
        ).round(1)
        return out

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Greedy unique assignment: sort all (player, pokemon) pairs globally by
    # normalized difference, then assign in order — each pokemon goes to at most one player
    flat_order   = np.argsort(norm_diff.ravel(), kind="stable")
    flat_players = flat_order // n_pokemon
    flat_pokemon = flat_order  % n_pokemon

    unique_idx        = np.full(n_players, -1, dtype=int)
    assigned_players = set()
    assigned_pokemon = set()

    for p, k in zip(flat_players, flat_pokemon):
        if p not in assigned_players and k not in assigned_pokemon:
            unique_idx[p] = k
            assigned_players.add(p)
            assigned_pokemon.add(k)
            if len(assigned_players) == n_players:
                break

    unique_out = build_output(unique_idx)
    unique_out.to_csv(output_file_unique, index=False)
    print(f"Saved {len(unique_out)} unique matches to {output_file_unique}")
    print(unique_out[["name", "pokemon_name", "total_stat_difference"]].head(10).to_string())

    # "True" best match per player, independent of other players — pokemon can repeat
    true_idx = np.argmin(norm_diff, axis=1)
    true_out = build_output(true_idx)
    true_out.to_csv(output_file_true, index=False)
    print(f"\nSaved {len(true_out)} true matches to {output_file_true}")
    print(true_out[["name", "pokemon_name", "total_stat_difference"]].head(10).to_string())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Match NBA players to Pokemon by base stats.")
    parser.add_argument("--season", default="2024-25", help="Season in form 'YYYY-YY' (e.g. 2024-25)")
    args = parser.parse_args()
    main(args.season)
