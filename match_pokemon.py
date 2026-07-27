import os
import numpy as np
import pandas as pd

INPUT_NBA  = os.path.join("data", "processed", "nba_pokemon_stats.csv")
INPUT_POKE = os.path.join("data", "raw", "pokemon_stats.csv")
OUTPUT_DIR = os.path.join("data", "processed")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "nba_pokemon_matches.csv")

STATS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]


def main():
    nba  = pd.read_csv(INPUT_NBA)
    poke = pd.read_csv(INPUT_POKE)

    poke["base_stat_total"] = poke[STATS].sum(axis=1)

    # Vectorized total absolute difference: (n_players, n_pokemon)
    nba_vals  = nba[STATS].values
    poke_vals = poke[STATS].values
    total_diff = ((nba_vals[:, np.newaxis, :] - poke_vals[np.newaxis, :, :]) ** 2).sum(axis=2)

    # Greedy unique assignment: sort all (player, pokemon) pairs globally by
    # difference, then assign in order — each pokemon goes to at most one player
    n_players, n_pokemon = total_diff.shape
    flat_order   = np.argsort(total_diff.ravel(), kind="stable")
    flat_players = flat_order // n_pokemon
    flat_pokemon = flat_order  % n_pokemon

    best_idx         = np.full(n_players, -1, dtype=int)
    assigned_players = set()
    assigned_pokemon = set()

    for p, k in zip(flat_players, flat_pokemon):
        if p not in assigned_players and k not in assigned_pokemon:
            best_idx[p] = k
            assigned_players.add(p)
            assigned_pokemon.add(k)
            if len(assigned_players) == n_players:
                break

    matched = poke.iloc[best_idx].reset_index(drop=True)

    out = nba[["PLAYER_ID", "name", "team"] + STATS + ["base_stat_total"]].copy()

    out["pokemon_id"]             = matched["id"].values
    out["pokemon_name"]           = matched["name"].values
    out["pokemon_type1"]          = matched["type1"].values
    out["pokemon_type2"]          = matched["type2"].values
    out["pokemon_hp"]             = matched["hp"].values
    out["pokemon_attack"]         = matched["attack"].values
    out["pokemon_defense"]        = matched["defense"].values
    out["pokemon_sp_attack"]      = matched["sp_attack"].values
    out["pokemon_sp_defense"]     = matched["sp_defense"].values
    out["pokemon_speed"]          = matched["speed"].values
    out["pokemon_base_stat_total"]= matched["base_stat_total"].values
    out["total_stat_difference"]  = np.sqrt(total_diff[np.arange(len(nba)), best_idx]).round(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(out)} matches to {OUTPUT_FILE}")
    print(out[["name", "pokemon_name", "total_stat_difference"]].head(10).to_string())


if __name__ == "__main__":
    main()
