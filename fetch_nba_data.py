import os
import time
import pandas as pd
from nba_api.stats.endpoints import (
    LeagueDashPlayerBioStats,
    LeagueDashPlayerStats,
    LeagueDashPtDefend,
    LeagueHustleStatsPlayer,
    DraftCombineStats,
)

SEASON = "2024-25"
DELAY = 1.0
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")


def fetch_bio_stats():
    print("Fetching bio stats (height, weight, age, team)...")
    time.sleep(DELAY)
    df = LeagueDashPlayerBioStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        per_mode_simple="PerGame",
    ).get_data_frames()[0]
    df = df[["PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "AGE", "PLAYER_HEIGHT", "PLAYER_WEIGHT"]].copy()
    df["PLAYER_HEIGHT"] = df["PLAYER_HEIGHT"].apply(
        lambda h: int(h.split("-")[0]) * 12 + int(h.split("-")[1]) if pd.notna(h) else None
    )
    return df


def fetch_base_stats():
    print("Fetching base stats (PPG, REB, AST, STL, BLK, TOV)...")
    time.sleep(DELAY)
    df = LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Base",
        per_mode_detailed="PerGame",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "PTS", "REB", "AST", "STL", "BLK", "TOV"]]


def fetch_advanced_stats():
    print("Fetching advanced stats (TS%, OffRtg, DefRtg)...")
    time.sleep(DELAY)
    df = LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "TS_PCT", "OFF_RATING", "DEF_RATING"]]


def fetch_on_ball_defense():
    print("Fetching on-ball defensive FG%...")
    time.sleep(DELAY)
    df = LeagueDashPtDefend(
        season=SEASON,
        season_type_all_star="Regular Season",
        defense_category="Overall",
        per_mode_simple="PerGame",
    ).get_data_frames()[0]
    return (
        df[["CLOSE_DEF_PERSON_ID", "D_FG_PCT"]]
        .rename(columns={
            "CLOSE_DEF_PERSON_ID": "PLAYER_ID",
            "D_FG_PCT": "ON_BALL_DEF_FG_PCT",
        })
    )


def fetch_hustle_stats():
    print("Fetching hustle stats (charges, loose balls, box outs)...")
    time.sleep(DELAY)
    df = LeagueHustleStatsPlayer(
        season=SEASON,
        season_type_all_star="Regular Season",
        per_mode_time="PerGame",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "CHARGES_DRAWN", "LOOSE_BALLS_RECOVERED", "BOX_OUTS"]]


def fetch_combine_stats():
    print("Fetching draft combine stats (2000-01 – 2024-25)...")
    seasons = [f"{y}-{str(y + 1)[-2:]}" for y in range(2000, 2025)]
    frames = []
    for season in seasons:
        try:
            time.sleep(DELAY)
            df = DraftCombineStats(
                season_all_time=season,
            ).get_data_frames()[0]
            if not df.empty:
                df["DRAFT_SEASON"] = season
                frames.append(df)
                print(f"  {season}: {len(df)} players")
        except Exception as e:
            print(f"  {season}: skipped ({e})")

    if not frames:
        print("  No combine data retrieved.")
        return pd.DataFrame(columns=["PLAYER_ID", "MAX_VERTICAL_LEAP", "LANE_AGILITY_TIME"])

    combined = pd.concat(frames, ignore_index=True)
    # One entry per player; keep the most recent season if a player appears twice
    combined = (
        combined
        .sort_values("DRAFT_SEASON")
        .groupby("PLAYER_ID", as_index=False)
        .last()
    )
    return combined[["PLAYER_ID", "MAX_VERTICAL_LEAP", "LANE_AGILITY_TIME"]]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    bio = fetch_bio_stats()
    base = fetch_base_stats()
    advanced = fetch_advanced_stats()
    defense = fetch_on_ball_defense()
    hustle = fetch_hustle_stats()
    combine = fetch_combine_stats()

    df = (
        bio
        .merge(base, on="PLAYER_ID", how="left")
        .merge(advanced, on="PLAYER_ID", how="left")
        .merge(defense, on="PLAYER_ID", how="left")
        .merge(hustle, on="PLAYER_ID", how="left")
        .merge(combine, on="PLAYER_ID", how="left")
    )

    df = df.rename(columns={
        "PLAYER_NAME":            "name",
        "TEAM_ABBREVIATION":      "team",
        "AGE":             "age",
        "PLAYER_HEIGHT":          "height",
        "PLAYER_WEIGHT":          "weight",
        "PTS":                    "ppg",
        "TS_PCT":                 "ts_pct",
        "ON_BALL_DEF_FG_PCT":     "on_ball_def_fg_pct",
        "BLK":                    "blk",
        "REB":                    "reb",
        "AST":                    "ast",
        "TOV":                    "tov",
        "OFF_RATING":             "off_rating",
        "STL":                    "stl",
        "DEF_RATING":             "def_rating",
        "MAX_VERTICAL_LEAP":      "combine_max_vertical",
        "LANE_AGILITY_TIME":      "combine_lane_agility",
        "CHARGES_DRAWN":          "charges_drawn",
        "LOOSE_BALLS_RECOVERED":  "loose_balls_recovered",
        "BOX_OUTS":               "box_outs",
    })

    output_cols = [
        "PLAYER_ID", "name", "team", "height", "weight", "age",
        "ppg", "ts_pct", "on_ball_def_fg_pct",
        "blk", "reb", "ast", "tov",
        "off_rating", "stl", "def_rating",
        "combine_max_vertical", "combine_lane_agility",
        "charges_drawn", "loose_balls_recovered", "box_outs",
    ]
    df = df[output_cols]

    out_path = os.path.join(OUTPUT_DIR, "nba_player_stats.csv")
    df.to_csv(out_path, index=False)
    print(f"\nDone. {len(df)} players saved to {out_path}")
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()
