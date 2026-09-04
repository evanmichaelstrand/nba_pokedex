# NBA Pokédex

Match every NBA player to their closest Pokémon based on how their real stat profile compares to a Pokémon's base stats. Built for social content (Instagram/TikTok), not scouting reports.

## How it works

1. **Fetch Pokémon stats** — pulls base stats (HP, Attack, Defense, Sp. Atk, Sp. Def, Speed) for all Pokémon from [PokéAPI](https://pokeapi.co/).
2. **Fetch NBA stats** — pulls per-game and advanced stats for every player in a season via the [`nba_api`](https://github.com/swar/nba_api) package (scoring, shooting splits, defense, hustle, on/off ratings, speed, etc.).
3. **Transform stats** — converts each player's raw stats into a 0–100ish Pokémon-style base stat line. Each Pokémon stat is a weighted composite of several normalized NBA inputs, then mapped onto the real Pokémon stat distribution via percentile:

   | Pokémon stat | Built from |
   |---|---|
   | HP | Total minutes played |
   | Attack | PPG + 2pt FG% |
   | Defense | Interior defensive FG% + blocks + rebounds |
   | Sp. Attack | (AST − TOV) + net offensive rating + 3-pt makes |
   | Sp. Defense | Perimeter defensive FG% + net defensive rating + steals |
   | Speed | Avg speed + loose balls recovered + charges drawn + box outs |

4. **Match to Pokémon** — computes the Euclidean distance between each player's stat line and every Pokémon's, normalized by combined stat total so high- and low-stat pairs are compared fairly. Produces two versions:
   - **Unique matches** — each Pokémon used at most once (greedy global assignment, best pairs win first).
   - **True matches** — each player's single best match regardless of reuse.

Only players with 500+ total minutes played are included, to filter out small sample sizes.

## Project structure

```
master.py                       # runs all four scripts in order for a given season
scripts/
  fetch_pokemon_data.py         # PokéAPI -> data/raw/pokemon_stats.csv
  fetch_nba_data.py             # nba_api -> data/raw/nba_player_stats_<season>.csv
  transform_stats.py            # raw NBA stats -> data/processed/nba_pokemon_stats_<season>.csv
  match_pokemon.py              # stat matching -> data/processed/nba_pokemon_matches_{unique,true}_<season>.csv
  season_utils.py               # shared season string helper (e.g. "2024-25" -> "2425")
```

`<season>` in filenames is the compact form of the season string, e.g. `2024-25` → `2425`.

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.9+.

## Usage

Run the full pipeline for a season:

```bash
python master.py 2024-25
```

Or run any step individually from the project root (each accepts an optional `--season`, default `2024-25`):

```bash
python scripts/fetch_pokemon_data.py
python scripts/fetch_nba_data.py --season 2024-25
python scripts/transform_stats.py --season 2024-25
python scripts/match_pokemon.py --season 2024-25
```

## Output

All output lands in `data/raw/` and `data/processed/`:

- `data/raw/pokemon_stats.csv` — all Pokémon base stats
- `data/raw/nba_player_stats_<season>.csv` — raw NBA player stats for the season
- `data/processed/nba_pokemon_stats_<season>.csv` — players converted to Pokémon-style stat lines
- `data/processed/nba_pokemon_matches_unique_<season>.csv` — final 1:1 player-to-Pokémon matches
- `data/processed/nba_pokemon_matches_true_<season>.csv` — each player's single best match (Pokémon may repeat)
