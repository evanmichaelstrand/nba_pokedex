# v2 Stat Plan

Draft of the NBA stats v2 will collect, grouped by the Pokémon stat each one feeds. Source details and coverage are in [stat_catalog.md](stat_catalog.md).

## HP

| Stat | Source | Status |
|---|---|---|
| Total minutes played (season) | `LeagueDashPlayerStats`, `measure_type_detailed_defense='Base'`, `per_mode_detailed='Totals'` → `MIN` | Available (0% null in v1 2025-26 data) |
| Total games played (season) | Same call → `GP` | Available (0% null in v1 2025-26 data) |

Both come from a single call per season.

## Attack

| Stat | Source | Status |
|---|---|---|
| Points per game (season) | `LeagueDashPlayerStats`, `measure_type_detailed_defense='Base'`, `per_mode_detailed='PerGame'` → `PTS` | Available (0% null in v1 2025-26 data) |
| Interior field goal % = 2-point FG% (season) | Same Base call as PPG → `(FGM − FG3M) / (FGA − FG3A)` | Available (v1's `fg2_pct`, 0% null among qualified players, 2025-26) |
| Total dunks (season) | `ShotChartDetail`, `team_id='0'`, `player_id='0'`, `context_measure_simple='FGA'`, one call per month → count made shots where `ACTION_TYPE` contains "Dunk" | Available (all 1,230 games, 2025-26) |

Notes:
- **Interior FG% definition:** decided: use 2-point FG% (includes mid-range jumpers and floaters, so it slightly favors rim finishers over mid-range scorers). If a stricter definition is ever needed, `LeagueDashPlayerShotLocations` → `Restricted Area FG_PCT` is one call per season (verified 2025-26, 0% null).
- **2-point FG% sample size:** qualified median is 267 2-point attempts; 39 qualified players have fewer than 100. Consider a minimum-attempts rule or shrinkage toward the league average.
- **Dunks:** don't use `DunkScoreLeaders` for counts (misses ~3%). Shot chart must be split by month: a single call is silently capped at 102,400 rows. Raw totals favor high-minute bigs; consider per-36.
- **Overlap:** 2-point FG% and dunks correlate 0.44 (made dunks are also made 2-pointers). That's related but not a full double count. PPG is nearly independent of both (−0.03 and 0.21).
- Cost: ~8 calls per season (1 Base `PerGame` call for PPG and 2-point FG%, ~7 monthly shot chart calls). The shot locations call is no longer needed.

## Defense

| Stat | Source | Status |
|---|---|---|
| Interior defensive FG% (season) | `LeagueDashPtDefend`, `defense_category='Less Than 6Ft'`, `per_mode_simple='Totals'` → `LT_06_PCT` (opponent FG% within 6 ft when this player is the closest defender); player ID column is `CLOSE_DEF_PERSON_ID` | Available (0% null among qualified, 2025-26) |
| Defensive rebounds (season) | `LeagueDashPlayerStats`, `measure_type_detailed_defense='Base'`, `per_mode_detailed='Totals'` → `DREB` | Available (0% null among qualified, 2025-26) |
| Blocks (season) | Same call → `BLK` | Available (0% null among qualified, 2025-26) |
| Shots contested (season) | `LeagueHustleStatsPlayer`, `per_mode_time='Totals'` → `CONTESTED_SHOTS` | Available (0% null among qualified, 2025-26; full from 2016-17) |

Notes:
- **Interior defensive FG%:** lower is better; invert when normalizing. The same call returns `FGA_LT_06` (rim attempts defended) and `PLUSMINUS` (= `LT_06_PCT` − `NS_LT_06_PCT`, how much below the shooters' normal FG% they held them). For a season-long stat, `LT_06_PCT` and `PLUSMINUS` rank players almost identically (correlation 1.00), so either works. Best with ≥200 attempts defended: Isaiah Stewart 0.396, Holmgren 0.453, Capela 0.453, Wembanyama 0.467.
- **Interior defensive FG% sample size:** qualified median is 158 rim attempts defended (min 32); 77 qualified players defended fewer than 100. Guards' values will be noisy. Use a minimum or shrink toward the league average using `FGA_LT_06`.
- **Defensive rebounds:** v1 used total rebounds; `DREB` is in the same Base call (`OREB` too). Leaders: Towns 656, Jokić 644, Jalen Johnson 639. Tracking alternatives in `LeagueDashPtStats` Rebounding (`DREB_CONTEST`, `DREB_CHANCE_PCT`) if effort/positioning matters more than volume.
- **Base call:** if Attack uses `PerGame` and Defense uses `Totals`, that's 2 Base calls; or fetch `Totals` once and compute PPG as `PTS / GP`.
- **Overlap (strong):** per 36 minutes, blocks and contested shots correlate 0.82; interior defensive FG% correlates −0.75 with blocks and −0.71 with contests (negative because lower FG% allowed is better); defensive rebounds correlate 0.54–0.60 with the others. All four mostly measure rim protection / size, so Defense will strongly favor centers. That may be the intent; if not, consider fewer of these or weighting them down.
- **Per-minute vs. totals:** DREB, BLK and contests are volume stats that reward minutes (already HP's job). Consider per-36 for these so HP and Defense don't double count playing time.
- Cost: 2–3 calls per season (PtDefend, hustle, plus the Base call shared with Attack/HP).

## Sp. Attack

| Stat | Source | Status |
|---|---|---|
| 3-pointers made (season) | `LeagueDashPlayerStats`, Base, `per_mode_detailed='Totals'` → `FG3M` | Available (0% null among qualified, 2025-26) |
| Net offensive rating (season) | `TeamPlayerOnOffSummary`, one call per team (30/season) → `OFF_RATING` on court (result set 1) − off court (result set 2), as in v1 | Available (v1's `net_off_rating`, 0% null among qualified, 2025-26) |
| Assists − turnovers (season) | Base Totals → `AST − TOV` | Available (0% null among qualified, 2025-26) |

Notes:
- **Net offensive rating:** on/off difference in team points per 100 possessions. Qualified range −16.1 to +13.4 (median −0.1). Leaders look right (Jokić +13.4, Jamal Murray +13.1, LaMelo Ball +12.6, SGA +11.1), but it's noisy and depends on teammates/backups: lower-minute players spread more (std 4.9 under 1,000 min vs 4.0 over 2,000). Most expensive stat in the plan (30 calls, ~1 s apart).
- **Assists − turnovers:** 21 qualified players are negative (mostly bigs). Leaders: Jokić 454, Cade Cunningham 398, Jamal Murray 364. Raw totals reward minutes; consider per-36.
- **3PM:** leaders Kon Knueppel 273, LaMelo Ball 272, Dončić 254. Volume stat that rewards minutes; consider per-36.
- **Overlap:** the three inputs are nearly independent (3PM / net off / AST−TOV correlate 0.09–0.16 per 36). Screen assists were dropped because they ran opposite to 3PM (−0.56) and AST−TOV (−0.30), which would have compressed Sp. Attack toward the middle.
- Cost: 30 additional calls per season (on/off). Base Totals is shared.

## Sp. Defense

| Stat | Source | Status |
|---|---|---|
| Net defensive rating (season) | `TeamPlayerOnOffSummary` (same 30 calls as net offensive rating) → `DEF_RATING` on − off | Available (0% null among qualified, 2025-26). **Fix traded players (see below).** |
| Steals (season) | `LeagueDashPlayerStats`, Base, `per_mode_detailed='Totals'` → `STL` | Available (0% null among qualified, 2025-26) |
| Deflections (season) | `LeagueHustleStatsPlayer`, `per_mode_time='Totals'` → `DEFLECTIONS` | Available (0% null among qualified, 2025-26) |
| Matchup FG% guarding guards (season) | `MatchupsRollup`, `per_mode_simple='Totals'` → rows with `POSITION='G'` → `MATCHUP_FG_PCT` (also `MATCHUP_FGA`, `PARTIAL_POSS`); player ID column is `DEF_PLAYER_ID` | Available (all 378 qualified, 2025-26) |

Notes:
- **Traded players' on/off (applies to net offensive and net defensive rating):** a traded player appears in each team's `TeamPlayerOnOffSummary`. v1 kept only the first row it saw (`drop_duplicates`, team list order), not the main team. Example: Jaren Jackson Jr.'s v1 net defensive rating of −29.9 is from 3 games / 72 min with UTA; his 45 games / 1,382 min with MEM were discarded. v2 should combine all teams weighted by minutes (`MIN` is in the on/off rows).
- **Net defensive rating is noisy:** lower is better; invert. Year-to-year correlation 0.33 (players qualified both 2024-25 and 2025-26, n=290; v1 data, which includes the trade bug). For comparison: steals 0.71, PPG 0.85.
- **Steals and deflections overlap heavily:** per 36, correlation **0.89**. Together they effectively double-weight one skill. Options: keep both but split the weight, or keep one.
- **Matchup FG% guarding guards** (replaces isolation defensive FG%, which was noise: year-to-year 0.02–0.24, median 32 FGA):
  - Opponent FG% on shots by guards while this player was the matched-up defender, across all possessions, not just isolations. Lower is better; invert.
  - Most stable perimeter-efficiency stat tested: year-to-year 0.31, about the same as net defensive rating (see the stability comparison in the catalog). Shot-based alternatives (v1's opponent 3PT FG%, beyond-15-ft FG%, Synergy perimeter play types) were all ~0.
  - Large sample: qualified median 260 FGA guarding guards; 9 qualified players under 100 (bigs who rarely guard guards). Consider shrinking those toward the league average.
  - Independent of height (−0.04) and steals (−0.01); 0.35 with interior defensive FG% (Defense).
  - Best with ≥200 FGA (2025-26): Tobias Harris .374, Devin Vassell .378, Jaylen Clark .385, Kevin Durant .387, Ausar Thompson .390. Known perimeter stoppers average the 64th percentile.
  - Only moderately reliable; consider a modest weight relative to steals/deflections (year-to-year 0.74 / 0.83).
  - Don't use `PLAYER_PTS / PARTIAL_POSS` from the same call: it measures who a player is assigned to guard (0.97 with opponent usage), not defense.
- **Overlap otherwise low:** net defensive rating vs. steals/deflections per 36 ≈ −0.2 (expected sign); matchup FG% ≈ 0 with steals.
- Cost: 1 extra call (`MatchupsRollup`). On/off, Base Totals and hustle are shared.

## Speed

| Stat | Source | Status |
|---|---|---|
| Offensive rebounds (season) | `LeagueDashPlayerStats`, Base, `per_mode_detailed='Totals'` → `OREB` | Available (0% null among qualified, 2025-26) |
| Loose balls recovered (season) | `LeagueHustleStatsPlayer`, `per_mode_time='Totals'` → `LOOSE_BALLS_RECOVERED` | Available (0% null among qualified, 2025-26) |
| Total transition points (season) | `SynergyPlayTypes`, `player_or_team_abbreviation='P'`, `play_type_nullable='Transition'`, `type_grouping_nullable='offensive'` → `PTS` | Available (368 of 378 qualified; missing = <10 transition possessions → fill 0) |
| Dribbles per touch (season) | `LeagueDashPtStats`, `player_or_team='Player'`, `pt_measure_type='Possessions'`, `per_mode_simple='Totals'` → `AVG_DRIB_PER_TOUCH` | Available (verified 2026-11-07: 582 players, 0% null) |

Notes:
- **None of these track measured speed:** per-36 correlations with tracked average speed (`AVG_SPEED`, used in v1) are −0.08 (OREB), 0.17 (loose balls), 0.00 (transition points), 0.02 (dribbles per touch). Speed here would mean hustle/activity and open-court scoring rather than how fast a player moves. If measured speed matters, `AVG_SPEED`, drives, and dunk `playerLateralSpeed` are in the catalog.
- **Offensive rebounds vs. dribbles per touch cancel out:** correlation **−0.58** (OREB tracks height at 0.62; dribbles per touch at −0.68). Bigs score high on one and low on the other, so the composite compresses toward the middle (the reason screen assists were dropped from Sp. Attack). Transition points also run opposite to OREB (−0.34).
- **Dribbles per touch:** measures ball dominance/handling style. Leaders: Jayson Tatum 5.75, Brandon Williams 5.39, Payton Pritchard 5.22; lowest: Robert Williams III 0.20, Gobert 0.22, Poeltl 0.25. It's already a rate, so no per-36 needed. Same call also returns `TOUCHES`, `TIME_OF_POSS`, `AVG_SEC_PER_TOUCH`, `FRONT_CT_TOUCHES`, paint/post/elbow touches.
- **Transition points:** Synergy `PTS` is from transition possessions the player finished (correlates 0.94 with fast-break points `PTS_FB`, the one-call alternative from Base `Misc`). Leaders: Maxey 485, Jaylen Brown 461, Alexander-Walker 451. Same call as transition FGA.
- **Leaders:** OREB Clingan 347, Gobert 299, Diabaté 273; loose balls Dyson Daniels 77, VJ Edgecombe 77, Gillespie 70.
- **Per-36:** OREB, loose balls and transition points are volume stats; consider per-36 to avoid overlapping with HP.
- Cost: 2 extra calls (Possessions tracking, Synergy transition). Base Totals and hustle are shared.

## Collection summary

About 43 API calls per season:

| Call | Count | Feeds |
|---|---|---|
| `LeagueDashPlayerStats` Base `Totals` (PPG = `PTS / GP`) | 1 | HP, Attack, Defense, Sp. Attack, Sp. Defense, Speed |
| `ShotChartDetail` league-wide, one per month | ~7 | Attack (dunks) |
| `LeagueDashPtDefend` `Less Than 6Ft` | 1 | Defense |
| `LeagueHustleStatsPlayer` `Totals` | 1 | Defense, Sp. Defense, Speed |
| `TeamPlayerOnOffSummary`, one per team | 30 | Sp. Attack, Sp. Defense |
| `MatchupsRollup` `Totals` | 1 | Sp. Defense |
| `SynergyPlayTypes` Transition (offensive) | 1 | Speed |
| `LeagueDashPtStats` Possessions | 1 | Speed |

Cross-cutting issues to settle before writing the script:
- **Per-36 vs. totals:** most counting stats reward minutes, which HP already measures.
- **Traded players:** combine on/off rows across teams weighted by minutes (v1 bug).
- **Missing Synergy rows:** players with <10 transition possessions are omitted. Fill transition points with 0.
- **Small samples:** 2PT FG% and interior defensive FG% need minimum attempts or shrinkage; matchup FG% guarding guards only for the few bigs under 100 FGA.
- **Opposing inputs:** OREB vs. dribbles per touch (Speed) pull in opposite directions by position, compressing that composite.
- **Redundant inputs:** steals vs. deflections (0.89), blocks vs. contests (0.82).
- **Lower-is-better stats:** interior defensive FG%, net defensive rating and matchup FG% guarding guards must be inverted.
