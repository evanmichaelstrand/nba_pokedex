"""Fetch base stats for every Pokémon species from PokéAPI, plus Mega forms by default.

Output: data/raw/pokemon_stats.csv. Species are discovered from PokéAPI's generation list, so new
generations are picked up automatically. Exits with an error if any Pokémon still fails after retries
(the file is still written, so a rerun only costs time).
"""
import argparse
import os
import sys
import time

import pandas as pd
import requests

BASE_URL = "https://pokeapi.co/api/v2"
DELAY = 0.2
TIMEOUT = 15
RETRIES = 3
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

session = requests.Session()


def get(url):
    for attempt in range(1, RETRIES + 1):
        try:
            time.sleep(DELAY)
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == RETRIES:
                raise
            time.sleep(2 * attempt)


def id_from_url(url):
    return int(url.rstrip("/").split("/")[-1])


def species_generations():
    """species id -> generation number, from PokéAPI's generation list."""
    gens = {}
    for g in get(f"{BASE_URL}/generation/?limit=100")["results"]:
        gen_num = id_from_url(g["url"])
        for s in get(g["url"])["pokemon_species"]:
            gens[id_from_url(s["url"])] = gen_num
    return gens


def select_pokemon(species_ids, forms):
    """Default form of every species, plus alternate forms per `forms`: 'none', 'mega' or 'all'."""
    listing = get(f"{BASE_URL}/pokemon/?limit=100000")["results"]
    selected = []
    for p in listing:
        pid = id_from_url(p["url"])
        if pid in species_ids:  # a species' default form shares its id
            selected.append((pid, p["name"]))
        elif forms == "all" or (forms == "mega" and "-mega" in p["name"]):
            selected.append((pid, p["name"]))
    return selected


def fetch_pokemon(pokemon_id, gens):
    data = get(f"{BASE_URL}/pokemon/{pokemon_id}")
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    types = [t["type"]["name"] for t in sorted(data["types"], key=lambda t: t["slot"])]
    species_id = id_from_url(data["species"]["url"])
    return {
        "id": data["id"],
        "name": data["name"],
        "species_id": species_id,
        "generation": gens.get(species_id),
        "is_default_form": data["is_default"],
        "type1": types[0] if types else None,
        "type2": types[1] if len(types) > 1 else None,
        "hp": stats.get("hp"),
        "attack": stats.get("attack"),
        "defense": stats.get("defense"),
        "sp_attack": stats.get("special-attack"),
        "sp_defense": stats.get("special-defense"),
        "speed": stats.get("speed"),
    }


def main(forms="mega"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Listing species by generation...")
    gens = species_generations()
    print(f"  {len(gens)} species across {len(set(gens.values()))} generations")

    to_fetch = select_pokemon(set(gens), forms)
    print(f"Fetching {len(to_fetch)} Pokémon (forms: {forms})...")
    records, failed = [], []
    for i, (pid, name) in enumerate(to_fetch, 1):
        try:
            records.append(fetch_pokemon(pid, gens))
        except Exception as e:
            failed.append(name)
            print(f"  {name} (id {pid}): failed after {RETRIES} attempts ({e})")
        if i % 100 == 0:
            print(f"  {i}/{len(to_fetch)} fetched...")

    df = pd.DataFrame(records).sort_values("id")
    out_path = os.path.join(OUTPUT_DIR, "pokemon_stats.csv")
    df.to_csv(out_path, index=False)
    print(f"\nDone. {len(df)} Pokémon saved to {out_path}")
    print(df.groupby("generation").size().rename("count").to_string())
    if failed:
        print(f"\nWARNING: {len(failed)} Pokémon missing after retries: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Pokémon base stats from PokéAPI.")
    parser.add_argument("--forms", choices=["none", "mega", "all"], default="mega",
                        help="Alternate forms to include besides each species' default form (default: mega)")
    args = parser.parse_args()
    main(args.forms)
