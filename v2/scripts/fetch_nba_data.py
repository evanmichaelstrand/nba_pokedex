"""Fetch the v2 NBA player stat set for one season.

Output: data/raw/nba_player_stats_<compact>.csv, one row per player who appeared in the season.
Stat choices, minimum samples and season availability are documented in docs/stat_plan.md;
endpoint details and quirks in docs/stat_catalog.md.

Players are not filtered by minutes here (the 500-minute filter belongs to the transform step),
but per-stat minimum samples are applied: below the minimum, that stat is null.
"""
import argparse
import calendar
import os
import time
from datetime import date

import pandas as pd
from nba_api.stats.endpoints import (
    LeagueDashPlayerStats,
    LeagueDashPtDefend,
    LeagueDashPtStats,
    LeagueHustleStatsPlayer,
    MatchupsRollup,
    PlayerIndex,
    ShotChartDetail,
    SynergyPlayTypes,
    TeamPlayerOnOffSummary,
)
from nba_api.stats.static import teams

from season_utils import parse_season, season_to_compact

DEFAULT_SEASON = "2025-26"
DELAY = 1.0  # seconds between calls; stats.nba.com throttles bursts
TIMEOUT = 60
RETRIES = 3
SHOT_CHART_ROW_CAP = 102400  # responses this size are silently truncated
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

# First season (start year) each source has complete data; earlier seasons leave its columns null.
FIRST_SEASON = {
    "on_off": 2007,
    "synergy": 2012,
    "tracking": 2013,
    "hustle": 2016,
    "matchups": 2017,
}

# stat -> (sample column, minimum). Below the minimum the stat is set to null.
MIN_SAMPLES = {
    "fg2_pct": ("fg2a", 70),
    "interior_def_fg_pct": ("interior_def_fga", 60),
    "matchup_fg_pct_vs_guards": ("matchup_fga_vs_guards", 100),
    "net_off_rating": ("on_court_min", 1000),  # optional in the plan; set to 0 to disable
}

OUTPUT_COLS = [
    "PLAYER_ID", "name", "team", "position", "gp", "total_min",
    # HP: total_min, gp
    # Attack
    "ppg", "fg2_pct", "fg2a", "dunks", "dunk_attempts",
    # Defense
    "interior_def_fg_pct", "interior_def_fga", "dreb", "blk", "contested_shots",
    # Sp. Attack
    "fg3m", "net_off_rating", "ast_minus_tov", "ast", "tov",
    # Sp. Defense
    "net_def_rating", "stl", "deflections", "charges_drawn", "matchup_fg_pct_vs_guards", "matchup_fga_vs_guards",
    # Speed
    "oreb", "loose_balls_recovered", "transition_pts", "drib_per_touch", "touches",
    # Sample sizes / context
    "on_court_min", "teams_played_for",
]


def call(endpoint_cls, **kwargs):
    """Instantiate an nba_api endpoint with spacing and retries."""
    for attempt in range(1, RETRIES + 1):
        time.sleep(DELAY)
        try:
            return endpoint_cls(timeout=TIMEOUT, **kwargs)
        except Exception as e:
            if attempt == RETRIES:
                raise
            print(f"    retry {attempt}/{RETRIES - 1} after error: {e}")
            time.sleep(DELAY * 5 * attempt)


def available(source, start_year):
    if start_year < FIRST_SEASON[source]:
        first = FIRST_SEASON[source]
        print(f"  skipped: no complete data before {first}-{str(first + 1)[-2:]}; columns left null")
        return False
    return True


def fetch_base(season):
    print("Fetching base totals (minutes, scoring, shooting, rebounds, assists, steals, blocks)...")
    df = call(LeagueDashPlayerStats, season=season, season_type_all_star="Regular Season",
              measure_type_detailed_defense="Base", per_mode_detailed="Totals").get_data_frames()[0]
    out = pd.DataFrame({
        "PLAYER_ID": df.PLAYER_ID,
        "name": df.PLAYER_NAME,
        "last_team": df.TEAM_ABBREVIATION,
        "gp": df.GP,
        "total_min": df.MIN,
        "ppg": df.PTS / df.GP,
        "fg2a": df.FGA - df.FG3A,
        "fg3m": df.FG3M,
        "oreb": df.OREB,
        "dreb": df.DREB,
        "ast": df.AST,
        "tov": df.TOV,
        "stl": df.STL,
        "blk": df.BLK,
    })
    out["fg2_pct"] = (df.FGM - df.FG3M) / out.fg2a.where(out.fg2a > 0)
    out["ast_minus_tov"] = out.ast - out.tov
    print(f"  {len(out)} players")
    return out


def fetch_positions(season):
    print("Fetching positions (player index; current listed position)...")
    df = call(PlayerIndex, season=season, historical_nullable="1").get_data_frames()[0]
    out = df[["PERSON_ID", "POSITION"]].rename(columns={"PERSON_ID": "PLAYER_ID", "POSITION": "position"})
    out["position"] = out.position.replace("", pd.NA)
    return out


def fetch_shots(season, start, end):
    """All shot attempts between two dates; splits the range if the response hits the row cap."""
    df = call(ShotChartDetail, team_id=0, player_id=0, context_measure_simple="FGA", season_nullable=season,
              season_type_all_star="Regular Season", date_from_nullable=start.strftime("%m/%d/%Y"),
              date_to_nullable=end.strftime("%m/%d/%Y")).get_data_frames()[0]
    if len(df) >= SHOT_CHART_ROW_CAP:
        if start == end:
            raise RuntimeError(f"Shot chart for a single day ({start}) hit the {SHOT_CHART_ROW_CAP}-row cap")
        mid = start + (end - start) // 2
        print(f"    {start}..{end} hit the row cap; splitting")
        return pd.concat([fetch_shots(season, start, mid), fetch_shots(season, mid + pd.Timedelta(days=1), end)])
    return df


def fetch_dunks(season, start_year):
    print("Fetching shot chart month by month (dunks)...")
    frames = []
    for year, month in [(start_year, m) for m in (10, 11, 12)] + [(start_year + 1, m) for m in range(1, 10)]:
        start = date(year, month, 1)
        if start > date.today():
            break
        end = date(year, month, calendar.monthrange(year, month)[1])
        df = fetch_shots(season, pd.Timestamp(start), pd.Timestamp(end))
        if len(df):
            print(f"  {start:%Y-%m}: {len(df)} shots")
            frames.append(df)
    shots = pd.concat(frames).drop_duplicates(["GAME_ID", "GAME_EVENT_ID"])
    print(f"  {len(shots)} shots across {shots.GAME_ID.nunique()} games")
    dunks = shots[shots.ACTION_TYPE.str.contains("Dunk", na=False)]
    return dunks.groupby("PLAYER_ID").agg(dunks=("SHOT_MADE_FLAG", "sum"), dunk_attempts=("SHOT_MADE_FLAG", "size")).reset_index()


def fetch_interior_defense(season, start_year):
    print("Fetching interior defense (opponent FG% within 6 ft)...")
    if not available("tracking", start_year):
        return None
    df = call(LeagueDashPtDefend, season=season, season_type_all_star="Regular Season",
              defense_category="Less Than 6Ft", per_mode_simple="Totals").get_data_frames()[0]
    return df.rename(columns={"CLOSE_DEF_PERSON_ID": "PLAYER_ID", "FGA_LT_06": "interior_def_fga",
                              "LT_06_PCT": "interior_def_fg_pct"})[["PLAYER_ID", "interior_def_fga", "interior_def_fg_pct"]]


def fetch_hustle(season, start_year):
    print("Fetching hustle stats (contested shots, deflections, charges, loose balls)...")
    if not available("hustle", start_year):
        return None
    df = call(LeagueHustleStatsPlayer, season=season, season_type_all_star="Regular Season",
              per_mode_time="Totals").get_data_frames()[0]
    return df.rename(columns={"CONTESTED_SHOTS": "contested_shots", "DEFLECTIONS": "deflections",
                              "CHARGES_DRAWN": "charges_drawn", "LOOSE_BALLS_RECOVERED": "loose_balls_recovered"})[
        ["PLAYER_ID", "contested_shots", "deflections", "charges_drawn", "loose_balls_recovered"]]


def fetch_on_off(season, start_year):
    """Net ratings and minutes per team. Traded players appear once per team: ratings are combined
    weighted by minutes, and the team with the most on-court minutes is recorded."""
    print("Fetching on/off ratings for all 30 teams...")
    if not available("on_off", start_year):
        return None
    cols = ["VS_PLAYER_ID", "MIN", "OFF_RATING", "DEF_RATING"]
    frames = []
    for team in teams.get_teams():
        dfs = call(TeamPlayerOnOffSummary, team_id=team["id"], season=season,
                   season_type_all_star="Regular Season").get_data_frames()
        on = dfs[1][cols].assign(court="on")
        off = dfs[2][cols].assign(court="off")
        frames.append(pd.concat([on, off]).assign(team=team["abbreviation"]))
        print(f"  {team['abbreviation']}: {len(on)} players")
    df = pd.concat(frames, ignore_index=True)
    df["w_off"] = df.OFF_RATING * df.MIN
    df["w_def"] = df.DEF_RATING * df.MIN
    totals = df.groupby(["VS_PLAYER_ID", "court"])[["MIN", "w_off", "w_def"]].sum()
    on, off = totals.xs("on", level="court"), totals.xs("off", level="court")
    on_rows = df[df.court == "on"]
    team_most_min = on_rows.loc[on_rows.groupby("VS_PLAYER_ID").MIN.idxmax()].set_index("VS_PLAYER_ID").team
    out = pd.DataFrame({
        "net_off_rating": on.w_off / on.MIN - off.w_off / off.MIN,
        "net_def_rating": on.w_def / on.MIN - off.w_def / off.MIN,
        "on_court_min": on.MIN,
        "team_most_min": team_most_min,
        "teams_played_for": on_rows.groupby("VS_PLAYER_ID").team.nunique(),
    })
    return out.rename_axis("PLAYER_ID").reset_index()


def fetch_matchups(season, start_year):
    print("Fetching matchup defense vs. guards...")
    if not available("matchups", start_year):
        return None
    df = call(MatchupsRollup, season=season, per_mode_simple="Totals").get_data_frames()[0]
    guards = df[df.POSITION == "G"]
    return guards.rename(columns={"DEF_PLAYER_ID": "PLAYER_ID", "MATCHUP_FGA": "matchup_fga_vs_guards",
                                  "MATCHUP_FG_PCT": "matchup_fg_pct_vs_guards"})[
        ["PLAYER_ID", "matchup_fga_vs_guards", "matchup_fg_pct_vs_guards"]]


def fetch_transition(season, start_year):
    print("Fetching transition points (Synergy)...")
    if not available("synergy", start_year):
        return None
    df = call(SynergyPlayTypes, season=season, season_type_all_star="Regular Season", player_or_team_abbreviation="P",
              play_type_nullable="Transition", type_grouping_nullable="offensive",
              per_mode_simple="Totals").get_data_frames()[0]
    return df.groupby("PLAYER_ID").PTS.sum().rename("transition_pts").reset_index()


def fetch_possessions(season, start_year):
    print("Fetching touches and dribbles per touch...")
    if not available("tracking", start_year):
        return None
    df = call(LeagueDashPtStats, season=season, season_type_all_star="Regular Season", player_or_team="Player",
              pt_measure_type="Possessions", per_mode_simple="Totals").get_data_frames()[0]
    return df.rename(columns={"AVG_DRIB_PER_TOUCH": "drib_per_touch", "TOUCHES": "touches"})[
        ["PLAYER_ID", "drib_per_touch", "touches"]]


def main(season=DEFAULT_SEASON):
    start_year = parse_season(season)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = fetch_base(season)
    sources = {
        "positions": fetch_positions(season),
        "dunks": fetch_dunks(season, start_year),
        "interior": fetch_interior_defense(season, start_year),
        "hustle": fetch_hustle(season, start_year),
        "on_off": fetch_on_off(season, start_year),
        "matchups": fetch_matchups(season, start_year),
        "transition": fetch_transition(season, start_year),
        "possessions": fetch_possessions(season, start_year),
    }
    for part in sources.values():
        if part is not None:
            df = df.merge(part, on="PLAYER_ID", how="left")

    # Counts where a missing row means none happened
    df[["dunks", "dunk_attempts"]] = df[["dunks", "dunk_attempts"]].fillna(0).astype(int)
    if sources["transition"] is not None:
        df["transition_pts"] = df.transition_pts.fillna(0)  # Synergy omits players with <10 possessions

    df["team"] = df.get("team_most_min", pd.Series(pd.NA, index=df.index)).fillna(df.last_team)

    for stat, (sample_col, minimum) in MIN_SAMPLES.items():
        if stat in df and sample_col in df and minimum:
            below = df[sample_col].isna() | (df[sample_col] < minimum)
            df.loc[below, stat] = pd.NA
            print(f"Min sample: {stat} null for {int(below.sum())} players ({sample_col} < {minimum})")

    df = df.reindex(columns=OUTPUT_COLS)
    out_path = os.path.join(OUTPUT_DIR, f"nba_player_stats_{season_to_compact(season)}.csv")
    df.to_csv(out_path, index=False)
    print(f"\nDone. {len(df)} players saved to {out_path}")
    print(df.head(3).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch the v2 NBA player stat set for a season.")
    parser.add_argument("--season", default=DEFAULT_SEASON, help="Season in form 'YYYY-YY' (e.g. 2025-26)")
    args = parser.parse_args()
    main(args.season)
