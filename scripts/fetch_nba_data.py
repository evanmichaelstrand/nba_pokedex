import argparse
import os
import time
import pandas as pd
from nba_api.stats.endpoints import (
    LeagueDashPlayerBioStats,
    LeagueDashPlayerStats,
    LeagueDashPtDefend,
    LeagueDashPtStats,
    LeagueHustleStatsPlayer,
    DraftCombineStats,
    TeamPlayerOnOffSummary,
)
from nba_api.stats.static import teams

from season_utils import season_to_compact

SEASON = "2025-26"
DELAY = 1.0
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw")


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
    print("Fetching base stats (PPG, REB, AST, STL, BLK, TOV, shooting splits)...")
    time.sleep(DELAY)
    df = LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Base",
        per_mode_detailed="PerGame",
    ).get_data_frames()[0]
    df = df[[
        "PLAYER_ID", "GP", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV",
        "FGM", "FGA", "FG3M", "FG3A", "FG3_PCT",
    ]].copy()
    df["fg2a"] = df["FGA"] - df["FG3A"]
    df["fg2_pct"] = (df["FGM"] - df["FG3M"]) / df["fg2a"]
    return df.rename(columns={"FG3A": "fg3a", "FG3_PCT": "fg3_pct"}).drop(columns=["FGM", "FG3M"])


def fetch_total_minutes():
    print("Fetching total minutes played...")
    time.sleep(DELAY)
    df = LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Base",
        per_mode_detailed="Totals",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "MIN"]].rename(columns={"MIN": "total_min"})


def fetch_advanced_stats():
    print("Fetching advanced stats (TS%)...")
    time.sleep(DELAY)
    df = LeagueDashPlayerStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "TS_PCT"]]


def fetch_on_off_ratings():
    print("Fetching on/off court ratings for all 30 teams...")
    all_teams = teams.get_teams()
    frames = []
    for team in all_teams:
        try:
            time.sleep(DELAY)
            dfs = TeamPlayerOnOffSummary(
                team_id=team["id"],
                season=SEASON,
                season_type_all_star="Regular Season",
            ).get_data_frames()
            on_df  = dfs[1][["VS_PLAYER_ID", "OFF_RATING", "DEF_RATING"]].rename(
                columns={"VS_PLAYER_ID": "PLAYER_ID", "OFF_RATING": "OFF_RATING_ON", "DEF_RATING": "DEF_RATING_ON"}
            )
            off_df = dfs[2][["VS_PLAYER_ID", "OFF_RATING", "DEF_RATING"]].rename(
                columns={"VS_PLAYER_ID": "PLAYER_ID", "OFF_RATING": "OFF_RATING_OFF", "DEF_RATING": "DEF_RATING_OFF"}
            )
            merged = on_df.merge(off_df, on="PLAYER_ID")
            frames.append(merged)
            print(f"  {team['abbreviation']}: {len(merged)} players")
        except Exception as e:
            print(f"  {team['abbreviation']}: skipped ({e})")

    combined = pd.concat(frames, ignore_index=True).drop_duplicates("PLAYER_ID")
    combined["net_off_rating"] = combined["OFF_RATING_ON"] - combined["OFF_RATING_OFF"]
    combined["net_def_rating"] = combined["DEF_RATING_ON"] - combined["DEF_RATING_OFF"]
    return combined[["PLAYER_ID", "net_off_rating", "net_def_rating"]]


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


def fetch_interior_defense():
    print("Fetching interior (rim) defensive FG%...")
    time.sleep(DELAY)
    df = LeagueDashPtDefend(
        season=SEASON,
        season_type_all_star="Regular Season",
        defense_category="Less Than 6Ft",
        per_mode_simple="PerGame",
    ).get_data_frames()[0]
    return (
        df[["CLOSE_DEF_PERSON_ID", "LT_06_PCT"]]
        .rename(columns={
            "CLOSE_DEF_PERSON_ID": "PLAYER_ID",
            "LT_06_PCT": "INTERIOR_DEF_FG_PCT",
        })
    )


def fetch_perimeter_defense():
    print("Fetching perimeter (3-point) defensive FG%...")
    time.sleep(DELAY)
    df = LeagueDashPtDefend(
        season=SEASON,
        season_type_all_star="Regular Season",
        defense_category="3 Pointers",
        per_mode_simple="PerGame",
    ).get_data_frames()[0]
    return (
        df[["CLOSE_DEF_PERSON_ID", "FG3_PCT"]]
        .rename(columns={
            "CLOSE_DEF_PERSON_ID": "PLAYER_ID",
            "FG3_PCT": "PERIMETER_DEF_FG_PCT",
        })
    )


def fetch_speed_stats():
    print("Fetching average player speed...")
    time.sleep(DELAY)
    df = LeagueDashPtStats(
        season=SEASON,
        season_type_all_star="Regular Season",
        player_or_team="Player",
        pt_measure_type="SpeedDistance",
        per_mode_simple="PerGame",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "AVG_SPEED"]]


def fetch_hustle_stats():
    print("Fetching hustle stats (charges, loose balls, box outs)...")
    time.sleep(DELAY)
    df = LeagueHustleStatsPlayer(
        season=SEASON,
        season_type_all_star="Regular Season",
        per_mode_time="PerGame",
    ).get_data_frames()[0]
    return df[["PLAYER_ID", "CHARGES_DRAWN", "LOOSE_BALLS_RECOVERED", "BOX_OUTS"]]


# turning this off, not used in v1
'''def fetch_combine_stats():
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
    return combined[["PLAYER_ID", "MAX_VERTICAL_LEAP", "LANE_AGILITY_TIME"]]'''


def main(season=None):
    global SEASON
    if season:
        SEASON = season

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    bio               = fetch_bio_stats()
    base              = fetch_base_stats()
    total_min         = fetch_total_minutes()
    advanced          = fetch_advanced_stats()
    on_off            = fetch_on_off_ratings()
    defense           = fetch_on_ball_defense()
    interior_defense  = fetch_interior_defense()
    perimeter_defense = fetch_perimeter_defense()
    speed             = fetch_speed_stats()
    hustle            = fetch_hustle_stats()
    #combine           = fetch_combine_stats()

    df = (
        bio
        .merge(base,              on="PLAYER_ID", how="left")
        .merge(total_min,         on="PLAYER_ID", how="left")
        .merge(advanced,          on="PLAYER_ID", how="left")
        .merge(on_off,            on="PLAYER_ID", how="left")
        .merge(defense,           on="PLAYER_ID", how="left")
        .merge(interior_defense,  on="PLAYER_ID", how="left")
        .merge(perimeter_defense, on="PLAYER_ID", how="left")
        .merge(speed,             on="PLAYER_ID", how="left")
        .merge(hustle,            on="PLAYER_ID", how="left")
        #.merge(combine,           on="PLAYER_ID", how="left")
    )

    df = df.rename(columns={
        "PLAYER_NAME":            "name",
        "TEAM_ABBREVIATION":      "team",
        "AGE":             "age",
        "PLAYER_HEIGHT":          "height",
        "PLAYER_WEIGHT":          "weight",
        "GP":                     "gp",
        "MIN":                    "min_pg",
        "PTS":                    "ppg",
        "TS_PCT":                 "ts_pct",
        "ON_BALL_DEF_FG_PCT":     "on_ball_def_fg_pct",
        "INTERIOR_DEF_FG_PCT":    "interior_def_fg_pct",
        "PERIMETER_DEF_FG_PCT":   "perimeter_def_fg_pct",
        "AVG_SPEED":              "avg_speed",
        "BLK":                    "blk",
        "REB":                    "reb",
        "AST":                    "ast",
        "TOV":                    "tov",
        "STL":                    "stl",
        #"MAX_VERTICAL_LEAP":      "combine_max_vertical",
        #"LANE_AGILITY_TIME":      "combine_lane_agility",
        "CHARGES_DRAWN":          "charges_drawn",
        "LOOSE_BALLS_RECOVERED":  "loose_balls_recovered",
        "BOX_OUTS":               "box_outs",
    })

    output_cols = [
        "PLAYER_ID", "name", "team", "height", "weight", "age",
        "gp", "min_pg", "total_min",
        "ppg", "ts_pct", "fg2_pct", "fg2a", "fg3_pct", "fg3a",
        "on_ball_def_fg_pct", "interior_def_fg_pct", "perimeter_def_fg_pct", "avg_speed",
        "blk", "reb", "ast", "tov",
        "net_off_rating", "stl", "net_def_rating",
        "charges_drawn", "loose_balls_recovered", "box_outs",
    ]
    df = df[output_cols]

    out_path = os.path.join(OUTPUT_DIR, f"nba_player_stats_{season_to_compact(SEASON)}.csv")
    df.to_csv(out_path, index=False)
    print(f"\nDone. {len(df)} players saved to {out_path}")
    print(df.head(3).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NBA player stats for a season.")
    parser.add_argument("--season", default=SEASON, help="Season in form 'YYYY-YY' (e.g. 2024-25)")
    args = parser.parse_args()
    main(args.season)
