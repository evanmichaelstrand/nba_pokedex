import os
import time
import requests
import pandas as pd

BASE_URL = "https://pokeapi.co/api/v2"
DELAY = 0.2
MAX_POKEMON_ID = 1025  # National dex ends here; IDs above this are alternate forms
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")


def fetch_pokemon(pokemon_id):
    r = requests.get(f"{BASE_URL}/pokemon/{pokemon_id}", timeout=10)
    r.raise_for_status()
    data = r.json()

    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    types = [t["type"]["name"] for t in data["types"]]

    return {
        "id":          data["id"],
        "name":        data["name"],
        "type1":       types[0] if len(types) > 0 else None,
        "type2":       types[1] if len(types) > 1 else None,
        "hp":          stats.get("hp"),
        "attack":      stats.get("attack"),
        "defense":     stats.get("defense"),
        "sp_attack":   stats.get("special-attack"),
        "sp_defense":  stats.get("special-defense"),
        "speed":       stats.get("speed"),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Fetching {MAX_POKEMON_ID} Pokémon from PokéAPI...")

    records = []
    for i in range(1, MAX_POKEMON_ID + 1):
        try:
            time.sleep(DELAY)
            records.append(fetch_pokemon(i))
            if i % 100 == 0:
                print(f"  {i}/{MAX_POKEMON_ID} fetched...")
        except Exception as e:
            print(f"  ID {i}: failed ({e})")

    df = pd.DataFrame(records)
    out_path = os.path.join(OUTPUT_DIR, "pokemon_stats.csv")
    df.to_csv(out_path, index=False)
    print(f"\nDone. {len(df)} Pokémon saved to {out_path}")
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()
