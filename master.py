import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

import fetch_pokemon_data
import fetch_nba_data
import transform_stats
import match_pokemon
from season_utils import season_to_compact


def main(season):
    season_to_compact(season)  # validate format up front, fail fast

    print(f"=== NBA Pokedex pipeline: season {season} ===\n")

    print("[1/4] Fetching Pokemon stats...")
    fetch_pokemon_data.main()

    print(f"\n[2/4] Fetching NBA player stats for {season}...")
    fetch_nba_data.main(season)

    print(f"\n[3/4] Transforming NBA stats into Pokemon-style stats for {season}...")
    transform_stats.main(season)

    print(f"\n[4/4] Matching NBA players to Pokemon for {season}...")
    match_pokemon.main(season)

    print(f"\n=== Pipeline complete for season {season} ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full NBA-Pokedex pipeline for a season.")
    parser.add_argument("season", help="Season in form 'YYYY-YY' (e.g. 2024-25)")
    args = parser.parse_args()
    main(args.season)
