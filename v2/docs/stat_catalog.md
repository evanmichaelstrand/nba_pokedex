# NBA Stat Catalog

Which NBA stats can be pulled via `nba_api`, how, and how complete they are. Maintained by the `check-stat-feasibility` skill (`.claude/skills/check-stat-feasibility/`); entries are verified with live calls, not just the nba_api docs.

**Status:** **Available**: works, good coverage · **Partial**: gaps, workaround needed, or limited seasons · **Not available**: no endpoint exposes it · **Unverified**: seen in nba_api source only, no live call yet

**Player pool reference (2025-26):** 582 players appeared; 378 had 500+ total minutes (v1's filter).

## By trait

| Trait | Best source | Status |
|---|---|---|
| Interior / zone FG% | `LeagueDashPlayerShotLocations` (Restricted Area, Paint, Mid-Range, 3PT zones) | Available |
| Dunk totals (made / attempted) | `ShotChartDetail` `ACTION_TYPE` contains "Dunk" | Available |
| Jump height | `DunkScoreLeaders.playerVertical` (in-game) · `DraftCombineStats.MAX_VERTICAL_LEAP` (pre-draft) | Partial |
| Explosiveness / burst | `DunkScoreLeaders` (`takeoffDistance`, `playerLateralSpeed`, `hangTime`) · `LeagueDashPtStats` Drives | Partial / Available |
| Speed | `LeagueDashPtStats` SpeedDistance `AVG_SPEED*` (average only) · combine `THREE_QUARTER_SPRINT` | Available / Partial |
| Endurance / motor | `LeagueDashPtStats` SpeedDistance `DIST_MILES*` · hustle stats | Available |
| Change of direction | combine `LANE_AGILITY_TIME`, `MODIFIED_LANE_AGILITY_TIME` | Partial (pre-draft only) |
| In-game top speed, acceleration, cutting/COD | none | Not available |
| Length / size | bio height/weight · combine `WINGSPAN`, `STANDING_REACH`, hand size | Available / Partial |
| Strength | combine `BENCH_PRESS` | Partial (17% coverage) |
| Ball handling / dominance | `LeagueDashPtStats` Possessions `AVG_DRIB_PER_TOUCH`, `TIME_OF_POSS` | Available |
| Play style (what a player does) | `SynergyPlayTypes` `POSS_PCT` | Available |
| Rebounding effort / positioning | `LeagueDashPtStats` Rebounding · hustle `BOX_OUTS` | Available |
| Defense | `LeagueDashPtDefend` · hustle · on/off · Synergy defensive | Available |
| Perimeter defensive efficiency | `MatchupsRollup` matchup FG% vs. guards (year-to-year 0.31); shot-based opponent FG% and Synergy defensive stats are noise (see stability comparison) | Partial |
| Transition FGA / scoring | `SynergyPlayTypes` Transition `FGA`, `POSS` · `LeagueDashPlayerStats` Misc `PTS_FB` | Available |
| Cuts | `SynergyPlayTypes` Cut `POSS` (finished cuts only) · `ShotChartDetail` "Cutting ..." shots | Available |
| Screen navigation (defense) | none direct; weak proxy: Synergy defensive `OffScreen` / `PRBallHandler` / `Handoff` volume | Not available |
| Screen setting (offense) | `LeagueHustleStatsPlayer` `SCREEN_ASSISTS` | Available |
| Deflections | `LeagueHustleStatsPlayer` `DEFLECTIONS` (2016-17+) | Available |
| Shots contested (defense) | `LeagueHustleStatsPlayer` `CONTESTED_SHOTS` (2016-17+) | Available |
| Shots taken while tightly guarded (offense) | `LeagueDashPlayerPtShot` by `close_def_dist_range_nullable` (2013-14+) | Available |

## Endpoints

### DunkScoreLeaders
- **Status:** Partial. Verified 2026-11-07 (2025-26, 2024-25).
- **Params:** `season`, **`player_id_nullable='0', team_id_nullable='0'`** (required workaround). One call returns the whole season.
- **Columns (55, one row per dunk):** `playerVertical` (in), `hangTime` (s), `takeoffDistance` (ft), `playerLateralSpeed`, `playerRotation`, `dunkScore`, `jumpSubscore`, `powerSubscore`, `styleSubscore`, `defensiveContestSubscore`, `maxBallHeight`, `ballSpeedThroughRim`, style flags (`reverseDunk`, `dunk360`, `throughTheLegs`, `alleyOop`, `tipIn`, `selfOop`), `jumpingFoot`, `dunkingHand`, pass details.
- **Coverage:** 2025-26: 11,533 dunks, 463 players, 262 with 10+ dunks, 0% null. 2024-25: 10,887 dunks. **2023-24 and earlier: HTTP 500, no data.**
- **Quirks:** With default params the API rejects `''` IDs (`"The value '' is invalid."`). With `'0'` it returns data, but nba_api 1.11.4 crashes parsing it (`KeyError: 'resultSet'`). Read the raw JSON instead: `pd.DataFrame(ep.nba_response.get_dict()['dunks'])` (`probe.py` does this automatically).
- **Completeness:** Covers all games (1,212 of 1,230 in 2025-26; the rest likely had no dunks), but undercounts made dunks by ~3% vs. `ShotChartDetail` (11,533 vs 11,939), up to ~10% for some bigs (Wembanyama 166 vs 178). Missed dunks are not included. Use `ShotChartDetail` for dunk counts and this feed for dunk biomechanics.
- **Caveat:** Biased toward players who dunk. Non-dunkers have no measurement. Aggregate per player as max or top-N mean with a minimum dunk count. Sanity check: max vertical leaders were Derrick Jones Jr. (42.0"), Shaedon Sharpe, Ja Morant.

### LeagueDashPtStats (player tracking)
Params: `player_or_team='Player'`, `pt_measure_type=<type>`, `per_mode_simple` (`PerGame`/`Totals`), `season`. One call per measure type per season.

| `pt_measure_type` | Key columns | Status |
|---|---|---|
| `SpeedDistance` | `AVG_SPEED`, `AVG_SPEED_OFF`, `AVG_SPEED_DEF`, `DIST_FEET`, `DIST_MILES`, `DIST_MILES_OFF`, `DIST_MILES_DEF` | Available (used in v1, 0% null among 500+ min players, 2025-26) |
| `Drives` | `DRIVES`, `DRIVE_FGM/FGA/FG_PCT`, `DRIVE_FTM/FTA`, `DRIVE_PTS`, `DRIVE_PTS_PCT`, `DRIVE_PASSES`, `DRIVE_AST`, `DRIVE_TOV`, `DRIVE_PF` (+ `_PCT` versions) | Available. Verified 2026-11-07, 582 players (2025-26) |
| `Rebounding` | `OREB/DREB/REB` × `_CONTEST`, `_UNCONTEST`, `_CONTEST_PCT`, `_CHANCES`, `_CHANCE_PCT`, `_CHANCE_DEFER`, `_CHANCE_PCT_ADJ`; `AVG_OREB_DIST`, `AVG_DREB_DIST`, `AVG_REB_DIST` | Available. Verified 2026-11-07, 578 players (2025-26) |
| `Possessions` | `TOUCHES`, `FRONT_CT_TOUCHES`, `TIME_OF_POSS`, `AVG_SEC_PER_TOUCH`, `AVG_DRIB_PER_TOUCH`, `PTS_PER_TOUCH`, `ELBOW_TOUCHES`, `POST_TOUCHES`, `PAINT_TOUCHES`, `PTS_PER_ELBOW/POST/PAINT_TOUCH`, `POINTS` | Available. Verified 2026-11-07, 582 players, 0% null (2025-26). Dribbles per touch leaders: Tatum 5.75, Pritchard 5.22; lowest: Robert Williams III 0.20, Gobert 0.22 |
| `CatchShoot`, `PullUpShot`, `Defense`, `Passing`, `ElbowTouch`, `PostTouch`, `PaintTouch`, `Efficiency` | — | Unverified |

Speed is an *average* over all court time; there is no top speed or acceleration.

### SynergyPlayTypes
- **Status:** Available. Verified 2026-10-26 and 2026-11-07 (2025-26).
- **Params:** **`player_or_team_abbreviation='P'`** (default is team), `play_type_nullable`, `type_grouping_nullable` (`offensive`/`defensive`), `per_mode_simple`, `season`. One call per play type × grouping (up to 18 per season).
- **Columns (same for every play type):** `POSS`, `POSS_PCT` (frequency), `PPP` (efficiency; on defense = allowed), `PERCENTILE` (NBA's rank, 0–1), `PTS`, `FGM`, `FGA`, `FGMX`, `FG_PCT`, `EFG_PCT`, `SCORE_POSS_PCT`, `TOV_POSS_PCT`, `FT_POSS_PCT`, `SF_POSS_PCT`, `PLUSONE_POSS_PCT`, `GP`.
- **Play types:** `Transition`, `Isolation`, `PRBallHandler`, `PRRollman`, `Postup`, `Spotup`, `Handoff`, `Cut`, `OffScreen`, `OffRebound` (putbacks), `Misc`.
- **Defensive coverage (2025-26 rows):** Isolation 394, PRBallHandler 415, PRRollman 386, Postup 329, Spotup 419, Handoff 313, OffScreen 317. **Transition, Cut, OffRebound, Misc: 0 rows (offense only).**
- **Offensive coverage examples:** Transition 409 players, Cut 339.
- **Cut detail (verified 2026-11-07):** `play_type_nullable='Cut'`, offensive. `POSS` = possessions *finished* by a cut (shot, foul or turnover after receiving the ball on a cut). 2025-26: 339 players, 0% null; 314 of 378 qualified players appear. **Synergy omits players with <10 possessions of a play type** (minimum in data = 10), so a missing player means ~0, not unknown: fill with 0. Qualified median 36 poss; 213 have ≥25. Leaders: Amen Thompson 263, Jarrett Allen 225 (5.3 per 36), Jalen Duren 219. History: 2014-15, 2015-16, 2016-17 all return ~335 players (earliest season not tested). Cross-check: correlates 0.88 with `ShotChartDetail` cutting shot attempts ("Cutting Layup/Dunk/Finger Roll Layup Shot": 8,974 FGA vs 16,522 Synergy possessions league-wide; Synergy also counts free throws, turnovers, and its own classification).
- **Transition detail (verified 2026-11-07):** `play_type_nullable='Transition'`, offensive. `FGA` = transition shot attempts the player took (`FGM + FGMX = FGA` exactly); `POSS` also counts transition possessions ending in free throws or turnovers. 2025-26: 409 players, 0% null; 368 of 378 qualified players (same <10-possession omission rule, so fill missing with 0). Qualified median 78 FGA. Leaders: Maxey 305 FGA, Mitchell 296, Jaylen Brown 294. History: 2016-17 (399 players; Westbrook 330), 2014-15 (426; Harden 302). Cross-check: correlates 0.92 with `PTS_FB` (fast-break points, `LeagueDashPlayerStats` Misc), a different definition with no FGA.
- **Defensive screen-related types (verified 2026-11-07, 2025-26):** "Possessions" = plays finished against this defender, so volume reflects who ends up guarding the shooter, not who navigated the screen.
  - `PRBallHandler`: 415 players, 362/378 qualified, median 174 poss. Volume led by drop/switch bigs (Gobert 806, Clingan 632, Jokić 603), not point-of-attack guards.
  - `Handoff`: 313 players, 304/378 qualified, median 31.
  - `OffScreen`: 317 players, 312/378 qualified, median 24, only 117 with ≥30. Most possessions go to wings who chase shooters (McDaniels 85, Christie 77).
  - `Isolation` (verified 2026-11-07, 2025-26 and 2024-25): 394 players (384 in 2024-25), 364/378 qualified. Median 32 FGA defended; 75 qualified with ≥50. `FG_PCT` year-to-year correlation 0.10 (both ≥30 FGA, n=135) and 0.24 (both ≥50, n=32): mostly noise.
  - **Defensive PPP is mostly noise:** OffScreen PPP vs PRBallHandler PPP correlate 0.05 (n=114). Best OffScreen PPP leaders (Saddiq Bey 0.33, Durant 0.61) don't pass a sanity check. Prefer volume/`POSS_PCT` (role) over PPP (skill) on defense.
- **Caveat:** Includes players with a handful of possessions. Apply a minimum `POSS` before using `PPP`/`PERCENTILE`. Athleticism-related play types: Transition, Cut, OffRebound.

### ShotChartDetail
- **Status:** Available. Verified 2026-11-07 (2025-26 full season; 2015-16 one month).
- **Params:** `team_id='0'`, `player_id='0'` (all players), `context_measure_simple='FGA'` (all attempts; default `'PTS'` returns makes only), `season_nullable`, and **`date_from_nullable`/`date_to_nullable` in `MM/DD/YYYY`, one month per call**.
- **Columns (one row per shot attempt):** `ACTION_TYPE` (e.g. "Cutting Dunk Shot", "Driving Floating Jump Shot"), `SHOT_TYPE` (2PT/3PT), `SHOT_ZONE_BASIC`, `SHOT_ZONE_AREA`, `SHOT_ZONE_RANGE`, `SHOT_DISTANCE` (ft), `LOC_X`, `LOC_Y`, `SHOT_MADE_FLAG`, `PERIOD`, clock, `GAME_ID`, `GAME_EVENT_ID`, `GAME_DATE`, player/team IDs. Second result set `LeagueAverages` = league FG% by zone.
- **Dunk totals:** filter `ACTION_TYPE` containing "Dunk" (11 types: Cutting, Running, Driving, Alley Oop, Running Alley Oop, Tip, Putback, Reverse, Running Reverse, Driving Reverse, plain). Group by `PLAYER_ID`, sum `SHOT_MADE_FLAG` = made, count = attempts. 2025-26: 11,939 made dunks, 467 players with ≥1, 344 of 378 qualified players. Leaders: Mobley 207, Thompson 201, Duren 189, Gobert 189, Wembanyama 178.
- **Coverage:** 2025-26 split by month: 219,160 shots across all 1,230 games. 2015-16 also returns data with the same dunk action types, so history goes back at least that far.
- **Quirk: row cap.** A full-season league-wide call returns exactly 102,400 rows and silently drops games. The cut was not by date: December and January were partially missing (139 games). Monthly calls (≤~46k rows) are complete. Dedupe on `GAME_ID` + `GAME_EVENT_ID` when combining.
- **Cost:** ~7 calls per season (one per month). Also useful for rim frequency, shot distance profiles, and shot-type mix (floaters, step-backs, fadeaways, etc.).

### LeagueDashPlayerShotLocations
- **Status:** Available. Verified 2026-11-07 (2025-26).
- **Params:** `per_mode_detailed='Totals'` (or `'PerGame'`), `season`. One call per season for all players (default `distance_range` = By Zone).
- **Columns:** `FGM`, `FGA`, `FG_PCT` for each zone: `Restricted Area`, `In The Paint (Non-RA)`, `Mid-Range`, `Left Corner 3`, `Right Corner 3`, `Corner 3`, `Above the Break 3`, `Backcourt`.
- **Quirk:** Two-level headers. nba_api returns (zone, stat) tuple columns. `probe.py` flattens them to `"Restricted Area FGA"` etc.; scripts must do the same.
- **Coverage:** 582 players; 0% null for Restricted Area / Paint / Mid-Range among all 378 qualified players (small nulls only in corner 3 and backcourt). Restricted Area FGA matches `ShotChartDetail` `SHOT_ZONE_BASIC` counts exactly, so this is the cheap substitute for aggregating the shot chart by zone.
- **Interior FG%:** qualified median 128 Restricted Area FGA; 40 players under 50 and 12 under 25 (e.g. Batum 2 FGA). RA FG% ranges 0.33–0.86 (median 0.66). Best with ≥100 FGA: Anthony Gill 0.836, Jericho Sims 0.834, Matković 0.817, Dončić 0.816, Ayton 0.801. Correlations: RA FG% vs made dunks 0.41, vs 2PT FG% 0.66. Dunks are a median 21% of a player's restricted-area makes.

### MatchupsRollup (defender matchup totals by opponent position)
- **Status:** Available. Verified 2026-11-07 (2025-26, 2024-25).
- **Params:** `per_mode_simple='Totals'`, `season`. One call per season, league-wide (no player/team needed).
- **Rows:** one per defender × `POSITION` of the player guarded: `G`, `F`, `C`, `TOTAL` (2,326 rows in 2025-26; `PERCENT_OF_TIME` sums to 2 per defender because of the TOTAL row).
- **Columns:** `PARTIAL_POSS`, `MATCHUP_MIN`, `PERCENT_OF_TIME`, `PLAYER_PTS` (points scored by the players guarded), `TEAM_PTS`, `MATCHUP_FGM/FGA/FG_PCT`, `MATCHUP_FG3M/FG3A/FG3_PCT`, `MATCHUP_FTM/FTA`, `MATCHUP_AST`, `MATCHUP_TOV`, `MATCHUP_BLK`, `SFL`, `GP`.
- **Coverage:** all 378 qualified players; median 1,321 partial possessions and 260 FGA guarding guards (9 qualified under 100 FGA).
- **Don't use points allowed per possession:** `PLAYER_PTS / PARTIAL_POSS` vs. guards correlates 0.97 with opponents' FGA per possession (usage) and −0.05 with their efficiency. It measures who a player is assigned to guard, not how well. That's also why its year-to-year correlation is a misleading 0.93.
- **Matchup FG% vs. guards (`POSITION='G'`, `MATCHUP_FG_PCT`)** is the best perimeter-efficiency option found: year-to-year 0.31, uncorrelated with height (−0.04) and steals (−0.01), 0.35 with interior defensive FG%. Best with ≥200 FGA (2025-26): Tobias Harris .374, Vassell .378, Jaylen Clark .385, Durant .387, Ausar Thompson .390.
- **Related:** `LeagueSeasonMatchups` has the same stats per defender × offensive player pair (plus `HELP_BLK`, `HELP_FGA/FGM`). Unverified.

### Perimeter defense: stability comparison (verified 2026-11-07)
Year-to-year correlation for players qualified in both 2024-25 and 2025-26 (n≈290); "stoppers" = median percentile of 14 well-known perimeter defenders (Daniels, Holiday, Dort, Caruso, Herb Jones, McDaniels, Anunoby, D. White, Amen/Ausar Thompson, Camara, Wallace, Suggs, Dunn).

| Stat | Year-to-year | Median sample | Stoppers | Notes |
|---|---|---|---|---|
| Opp 3PT FG% as closest defender (`LeagueDashPtDefend` 3 Pointers; v1) | −0.01 | 209 3PA | — | Pure noise |
| Same, vs. shooters' normal (`PLUSMINUS`) | −0.02 | 209 | — | Pure noise |
| Opp FG% beyond 15 ft (`Greater Than 15Ft`) | 0.06 | 242 | — | Noise |
| Synergy isolation FG% | 0.02 | 32 FGA | — | Noise |
| Synergy perimeter types combined PPP (Iso+PnR handler+Spot-up+Off-screen+Handoff) | 0.02 | 430 poss | — | Noise despite large sample |
| Matchup FG% vs. guards (`MatchupsRollup`) | 0.31 | 1,321 poss | 64th | Best perimeter-specific option |
| Overall opp FG% vs. normal (`LeagueDashPtDefend` Overall `PCT_PLUSMINUS`) | 0.51 (0.38 for ≤6'7") | 490 FGA | 76th | Not perimeter: 0.71 with interior def FG%, −0.39 with height |
| Matchup pts per 100 poss vs. guards | 0.93 | 1,321 | 58th | Measures assignment (0.97 with opponent usage) |
| 3PT contests per 36 (hustle) | 0.80 | — | 71st | Activity, not efficiency; tilts to bigs (0.44 with height) |
| Deflections per 36 | 0.83 | — | 82nd | 0.88 with steals |
| Steals per 36 (reference) | 0.74 | — | — | |

### DraftCombineStats (also `DraftCombineDrillResults`, `DraftCombinePlayerAnthro`)
- **Status:** Partial. Verified 2026-11-07.
- **Params:** `season_all_time` = a season like `'2025-26'` (one draft class, 47 cols incl. shooting drills) or `'All Time'` (2000–2026 classes, 1,873 rows, 24 cols: measurements + athletic drills, no shooting drills).
- **Columns:** `MAX_VERTICAL_LEAP`, `STANDING_VERTICAL_LEAP`, `LANE_AGILITY_TIME`, `MODIFIED_LANE_AGILITY_TIME`, `THREE_QUARTER_SPRINT`, `BENCH_PRESS`, `WINGSPAN`, `STANDING_REACH`, `HAND_LENGTH`, `HAND_WIDTH`, `BODY_FAT_PCT`, `HEIGHT_WO_SHOES`, `HEIGHT_W_SHOES`, `WEIGHT`.
- **Coverage of the 378 qualified 2025-26 players (latest combine per player):** wingspan / standing reach 67%; max vertical, lane agility, ¾ sprint 55%; bench press 17%.
- **Caveats:** Measured once before the draft, years out of date for veterans. Missing for players who skipped the combine (many internationals, older players) or individual drills. In the 2025 class, `BENCH_PRESS`, `BODY_FAT_PCT` and `HEIGHT_W_SHOES` are 100% null.

### Endpoints used by v1 (verified via v1's 2025-26 raw data: 0% null among 500+ min players except `weight` 0.3%)
- **LeagueDashPlayerBioStats** (`per_mode_simple='PerGame'`): `PLAYER_HEIGHT` ("6-7" string; v1 converts to inches), `PLAYER_WEIGHT`, `AGE`, `TEAM_ABBREVIATION`.
- **LeagueDashPlayerStats**: `measure_type_detailed_defense='Base'` (per game: `PTS`, `REB`, `AST`, `STL`, `BLK`, `TOV`, `FGM/FGA`, `FG3M/FG3A/FG3_PCT`, `MIN`, `GP`; `per_mode_detailed='Totals'` for total minutes) and `'Advanced'` (`TS_PCT`). `'Misc'` verified 2026-11-07 (2025-26, 582 players): `PTS_FB` (fast-break points), `PTS_OFF_TOV`, `PTS_2ND_CHANCE`, `PTS_PAINT`, `BLKA` (shots blocked), `PFD` (fouls drawn), `OPP_*` versions (points allowed while on court). Points only, no attempts.
- **LeagueDashPtDefend** (opponent FG% when guarded): `defense_category='Overall'` → `D_FG_PCT`; `'Less Than 6Ft'` → `LT_06_PCT` (rim); `'3 Pointers'` → `FG3_PCT` (perimeter). Player ID column is `CLOSE_DEF_PERSON_ID`. Also `'2 Pointers'`, `'Less Than 10Ft'`, `'Greater Than 15Ft'` (Unverified). `'Less Than 6Ft'` with `per_mode_simple='Totals'` verified 2026-11-07 (2025-26): 576 players; columns `FGM_LT_06`, `FGA_LT_06` (attempts defended), `LT_06_PCT`, `NS_LT_06_PCT` (shooters' normal FG%), `PLUSMINUS` (= difference), `FREQ`. Qualified median 158 rim FGA defended, 77 of 378 under 100. Best with ≥200: Isaiah Stewart 0.396, Holmgren 0.453, Capela 0.453.
- **LeagueDashPlayerStats Base `Totals`** verified 2026-11-07 (2025-26, 582 players, 69 cols incl. rank columns): includes `OREB`, `DREB` (v1 only used `REB`), `BLK`, `BLKA`, `PF`, `PFD`, `PLUS_MINUS`.
- **LeagueHustleStatsPlayer**: v1 uses `CHARGES_DRAWN`, `LOOSE_BALLS_RECOVERED`, `BOX_OUTS`. `SCREEN_ASSISTS` (offense: screens set that led directly to a basket) verified 2026-11-07, 2025-26: 0% null; leaders Gobert 307, Queta 276, Ayton 268. Source also lists `OFF_/DEF_LOOSE_BALLS_RECOVERED`, `SCREEN_AST_PTS`, `BOX_OUT_PLAYER_REBS`, `PCT_BOX_OUTS_*` (Unverified). `CONTESTED_SHOTS` and `DEFLECTIONS`: see below.

### LeagueHustleStatsPlayer: deflections
- **Status:** Available. Verified 2026-11-07 (2025-26, 2016-17).
- **Params:** `per_mode_time='Totals'`, `season`. Same call as contested shots (one per season).
- **Column:** `DEFLECTIONS` (tipped/deflected passes and dribbles; no offensive/defensive split).
- **Coverage:** 2025-26: 581 players, 0% null (8 zeros), all 378 qualified players. 2016-17: 485 players. Same history as other hustle stats (full from 2016-17).
- **Leaders 2025-26:** totals Cason Wallace 339, Ausar Thompson 321, Dyson Daniels 316. Per 36 (500+ min): Dru Smith 6.18, Ausar Thompson 6.10, Alex Caruso 6.07. 2016-17 totals: John Wall 304, Draymond Green 295.
- **Caveat:** Strongly correlated with steals (r = 0.88 per minute, 0.95 as totals). Using both in one composite double-counts the same skill. Pick one, or weight them knowing they overlap.

### LeagueHustleStatsPlayer: contested shots (defense)
- **Status:** Available. Verified 2026-11-07 (2025-26, 2016-17, 2015-16).
- **Params:** `per_mode_time='Totals'` (or `'PerGame'`, `'Per36'`), `season`. One call per season.
- **Columns:** `CONTESTED_SHOTS` = shots the player contested on defense; `CONTESTED_SHOTS_2PT` + `CONTESTED_SHOTS_3PT` = total exactly. `MIN` included for per-minute rates.
- **Coverage:** 2025-26: 581 players, 0% null, all 378 qualified players. Totals leader Donovan Clingan 1,038 (Gobert 807, Huff 700). Per 36: Clingan 17.8, Kornet 16.4, Kalkbrenner 15.7.
- **History:** 2016-17: 485 players (full). **2015-16: only 147 players (partial; hustle tracking began that season).** Treat 2016-17 as the first usable season.
- **Caveat:** Volume stat dominated by rim-protecting bigs. Normalize by minutes, and use the 3PT split for perimeter defense.

### LeagueDashPlayerPtShot: shots taken while tightly guarded (offense)
- **Status:** Available. Verified 2026-11-07 (2025-26, 2014-15, 2013-14, 2012-13).
- **Params:** `close_def_dist_range_nullable` = `'0-2 Feet - Very Tight'`, `'2-4 Feet - Tight'`, `'4-6 Feet - Open'`, `'6+ Feet - Wide Open'` (exact strings, not enumerated in nba_api); `per_mode_simple='Totals'`, `season`. One call per range per season; "contested" = Very Tight + Tight (2 calls).
- **Columns:** `FGA`, `FGM`, `FG_PCT`, `EFG_PCT`, `FGA_FREQUENCY` (share of the player's shots in this range), `FG2A/FG2M/FG2_PCT`, `FG3A/FG3M/FG3_PCT`, `GP`. Team column is `PLAYER_LAST_TEAM_ABBREVIATION`.
- **Coverage:** 2025-26: Very Tight 553 players, Tight 573. `FG3_PCT` is null when a player had 0 attempts in that range. Leaders: Very Tight FGA Sengun 300, Jaylen Brown 249; Tight FGA Durant 882, Jaylen Brown 634.
- **History:** 2013-14 onward. 2012-13 returns 0 rows.
- **Related:** `PlayerDashPtShots` (per player, `CLOSE_DEF_DIST_RANGE` breakdown) and `BoxScorePlayerTrackV3` (`contestedFieldGoalsAttempted`, per game) give the same idea at higher cost.
- **TeamPlayerOnOffSummary**: one call per team (30/season). Result sets 1 (on) and 2 (off) give `OFF_RATING`/`DEF_RATING`, plus `GP`, `MIN`; v1 computes on − off. **Traded players appear once per team** (verified 2026-11-07: Jaren Jackson Jr. 2025-26 = MEM 45 GP / 1,382 min and UTA 3 GP / 72 min). v1's `drop_duplicates("PLAYER_ID")` keeps whichever team comes first in `teams.get_teams()` order, so its values for traded players can come from tiny stints. Combine teams weighted by `MIN` instead. Year-to-year correlation (v1 data, 2024-25 → 2025-26, n=290): net offensive 0.40, net defensive 0.33.

### Unverified leads
- **BoxScorePlayerTrackV3**: per-game `speed`, `distance`, `touches`, contested/uncontested FG. One call per game (~1,230/season).
- **BoxScoreHustleV2**: per-game hustle including `deflections`, `contestedShots`.
- **PlayerDashPtReb**, **PlayerDashPtShots**: per-player rebound/shot breakdowns by distance and how closely the nearest defender was guarding.

## Not available
- In-game top speed, acceleration, change of direction, deceleration: only average speed is exposed. *(checked 2026-10-26)*
- Jump height outside dunks (rebounds, blocks, jump shots). *(checked 2026-10-26)*
- Screen navigation (how well a defender gets over/under/through screens): no screen-level defensive data in any endpoint. Only `screenAssists` (offense) and `switchesOn` (per-game matchups) mention screens/switches. Synergy defensive play types are the closest proxy, but their PPP is noise. *(checked 2026-11-07)*
- Every cut a player makes, including cuts where they don't get the ball: only finished cuts (Synergy) or cutting shots (shot chart) exist. *(checked 2026-11-07)*
- Dunk tracking before 2024-25. *(checked 2026-11-07)*
