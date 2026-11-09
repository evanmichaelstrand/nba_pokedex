# v2 Stat Plan

Draft of the NBA stats v2 will collect, grouped by the Pokémon stat each one feeds. Source details and coverage are in [stat_catalog.md](stat_catalog.md).

All players under 500 total minutes are dropped first. **Min sample** is an extra per-stat requirement: a player below it gets null for that stat (see [Minimum samples](#minimum-samples)). **Since** is the first season with complete data (see [Season availability](#season-availability)).

## HP

| Stat | Source | Min sample | Since |
|---|---|---|---|
| Total minutes played (season) | `LeagueDashPlayerStats`, `measure_type_detailed_defense='Base'`, `per_mode_detailed='Totals'` → `MIN` | — | 1996-97 |
| Total games played (season) | Same call → `GP` | — | 1996-97 |

Both come from a single call per season. 0% null for qualified players (2025-26).

## Attack

| Stat | Source | Min sample | Since |
|---|---|---|---|
| Points per game (season) | Base `Totals` call → `PTS / GP` | — | 1996-97 |
| Interior field goal % = 2-point FG% (season) | Same call → `(FGM − FG3M) / (FGA − FG3A)` | **70 2PA** (13 of 378 null, 2025-26) | 1996-97 |
| Total dunks (season) | `ShotChartDetail`, `team_id='0'`, `player_id='0'`, `context_measure_simple='FGA'`, one call per month → count made shots where `ACTION_TYPE` contains "Dunk" | — | 1996-97 |

Notes:
- **Interior FG% definition:** decided: use 2-point FG% (includes mid-range jumpers and floaters, so it slightly favors rim finishers over mid-range scorers). If a stricter definition is ever needed, `LeagueDashPlayerShotLocations` → `Restricted Area FG_PCT` is one call per season (verified 2025-26, 0% null).
- **2-point FG% sample size:** stabilizes at ~67 attempts; qualified median is 266. Players with ≥67 2PA in both seasons carry over at 0.66 year to year vs. 0.21 for the rest.
- **Dunks:** don't use `DunkScoreLeaders` for counts (misses ~3%; only exists from 2024-25). Shot chart must be split by month: a single call is silently capped at 102,400 rows. Raw totals favor high-minute bigs; consider per-36.
- **Overlap:** 2-point FG% and dunks correlate 0.44 (made dunks are also made 2-pointers). That's related but not a full double count. PPG is nearly independent of both (−0.03 and 0.21).
- Cost: ~8 calls per season (Base `Totals` shared; ~7 monthly shot chart calls).

## Defense

| Stat | Source | Min sample | Since |
|---|---|---|---|
| Interior defensive FG% (season) | `LeagueDashPtDefend`, `defense_category='Less Than 6Ft'`, `per_mode_simple='Totals'` → `LT_06_PCT` (opponent FG% within 6 ft when this player is the closest defender); player ID column is `CLOSE_DEF_PERSON_ID` | **60 rim FGA defended** (`FGA_LT_06`; 20 of 378 null) | 2013-14 |
| Defensive rebounds (season) | Base `Totals` → `DREB` | — | 1996-97 |
| Blocks (season) | Base `Totals` → `BLK` | — | 1996-97 |
| Shots contested (season) | `LeagueHustleStatsPlayer`, `per_mode_time='Totals'` → `CONTESTED_SHOTS` | — | 2016-17 |

Notes:
- **Interior defensive FG%:** lower is better; invert when normalizing. The same call returns `FGA_LT_06` (rim attempts defended) and `PLUSMINUS` (= `LT_06_PCT` − `NS_LT_06_PCT`, how much below the shooters' normal FG% they held them). For a season-long stat, `LT_06_PCT` and `PLUSMINUS` rank players almost identically (correlation 1.00), so either works. Best with ≥200 attempts defended: Isaiah Stewart 0.396, Holmgren 0.453, Capela 0.453, Wembanyama 0.467.
- **Interior defensive FG% sample size:** stabilizes at ~57 rim attempts; qualified median is 158. Above it in both seasons: year-to-year 0.74 vs. 0.23 below.
- **Defensive rebounds:** v1 used total rebounds; `DREB` is in the same Base call (`OREB` too). Leaders: Towns 656, Jokić 644, Jalen Johnson 639. Tracking alternatives in `LeagueDashPtStats` Rebounding (`DREB_CONTEST`, `DREB_CHANCE_PCT`) if effort/positioning matters more than volume.
- **Overlap (strong):** per 36 minutes, blocks and contested shots correlate 0.82; interior defensive FG% correlates −0.75 with blocks and −0.71 with contests (negative because lower FG% allowed is better); defensive rebounds correlate 0.54–0.60 with the others. All four mostly measure rim protection / size, so Defense will strongly favor centers. That may be the intent; if not, consider fewer of these or weighting them down.
- **Per-minute vs. totals:** DREB, BLK and contests are volume stats that reward minutes (already HP's job). Consider per-36 for these so HP and Defense don't double count playing time.
- Cost: 2 calls per season (PtDefend, hustle) plus the shared Base call.

## Sp. Attack

| Stat | Source | Min sample | Since |
|---|---|---|---|
| 3-pointers made (season) | Base `Totals` → `FG3M` | — | 1996-97 |
| Net offensive rating (season) | `TeamPlayerOnOffSummary`, one call per team (30/season) → `OFF_RATING` on court (result set 1) − off court (result set 2); combine traded players' teams weighted by `MIN` | **1,000 on-court minutes** (99 of 378 null), optional; see note | 2007-08 |
| Assists − turnovers (season) | Base `Totals` → `AST − TOV` | — | 1996-97 |

Notes:
- **Net offensive rating:** on/off difference in team points per 100 possessions. Leaders look right (Jokić +13.4, Jamal Murray +13.1, LaMelo Ball +12.6, SGA +11.1). With the traded-player fix, year-to-year correlation is 0.43. It's much noisier for low-minute players: 0.22 for players under 1,000 on-court minutes vs. 0.45 at 1,500+. The 1,000-minute minimum nulls about a quarter of qualified players, a bigger cut than any other stat; alternative: no minimum and a lower weight. Off-court minutes don't matter (every qualified player has 1,000+). Most expensive stat in the plan (30 calls, ~1 s apart).
- **Assists − turnovers:** 21 qualified players are negative (mostly bigs). Leaders: Jokić 454, Cade Cunningham 398, Jamal Murray 364. Raw totals reward minutes; consider per-36.
- **3PM:** leaders Kon Knueppel 273, LaMelo Ball 272, Dončić 254. Volume stat that rewards minutes; consider per-36.
- **Overlap:** the three inputs are nearly independent (3PM / net off / AST−TOV correlate 0.09–0.16 per 36). Screen assists were dropped because they ran opposite to 3PM (−0.56) and AST−TOV (−0.30), which would have compressed Sp. Attack toward the middle.
- Cost: 30 additional calls per season (on/off). Base Totals is shared.

## Sp. Defense

| Stat | Source | Min sample | Since |
|---|---|---|---|
| Net defensive rating (season) | `TeamPlayerOnOffSummary` (same 30 calls as net offensive rating) → `DEF_RATING` on − off; combine traded players' teams weighted by `MIN` | — (more minutes don't make it more stable) | 2007-08 |
| Steals (season) | Base `Totals` → `STL` | — | 1996-97 |
| Deflections (season) | `LeagueHustleStatsPlayer`, `per_mode_time='Totals'` → `DEFLECTIONS` | — | 2016-17 |
| Matchup FG% guarding guards (season) | `MatchupsRollup`, `per_mode_simple='Totals'` → rows with `POSITION='G'` → `MATCHUP_FG_PCT` (also `MATCHUP_FGA`, `PARTIAL_POSS`); player ID column is `DEF_PLAYER_ID` | **100 FGA guarded** (`MATCHUP_FGA`; 9 of 378 null), a floor only; see note | **2017-18** |

Notes:
- **Traded players' on/off (applies to net offensive and net defensive rating):** a traded player appears in each team's `TeamPlayerOnOffSummary`. v1 kept only the first row it saw (`drop_duplicates`, team list order), not the main team. Example: Jaren Jackson Jr.'s v1 net defensive rating of −29.9 is from 3 games / 72 min with UTA; combining both teams by minutes gives −6.8. 49 qualified players were traded in 2025-26.
- **Net defensive rating is noisy:** lower is better; invert. Year-to-year correlation 0.39 with the trade fix (0.33 in v1's data). Unlike net offensive rating, it doesn't get more stable with more minutes (0.39 at 500–1,000 on-court minutes, 0.33 at 1,500+), so a minimum wouldn't help. For comparison: steals 0.74, PPG 0.85.
- **Steals and deflections overlap heavily:** per 36, correlation **0.89**. Together they effectively double-weight one skill. Options: keep both but split the weight, or keep one.
- **Matchup FG% guarding guards** (replaces isolation defensive FG%, which was noise: year-to-year 0.02–0.24, median 32 FGA):
  - Opponent FG% on shots by guards while this player was the matched-up defender, across all possessions, not just isolations. Lower is better; invert.
  - Most stable perimeter-efficiency stat tested: year-to-year 0.31, about the same as net defensive rating (see the stability comparison in the catalog). Shot-based alternatives (v1's opponent 3PT FG%, beyond-15-ft FG%, Synergy perimeter play types) were all ~0.
  - **No minimum makes it reliable.** Players differ very little in true skill here, so it stabilizes only around ~850 FGA guarded; no qualified player gets there (max 604, median 260). At the median it's ~23% signal. The 100-FGA floor just removes the 9 bigs who barely guard guards. Raising it doesn't buy much: 200 FGA nulls 113 players for ~19% signal. Keep its weight modest.
  - Independent of height (−0.04) and steals (−0.01); 0.35 with interior defensive FG% (Defense).
  - Best with ≥200 FGA (2025-26): Tobias Harris .374, Devin Vassell .378, Jaylen Clark .385, Kevin Durant .387, Ausar Thompson .390. Known perimeter stoppers average the 64th percentile.
  - Don't use `PLAYER_PTS / PARTIAL_POSS` from the same call: it measures who a player is assigned to guard (0.97 with opponent usage), not defense.
- **Overlap otherwise low:** net defensive rating vs. steals/deflections per 36 ≈ −0.2 (expected sign); matchup FG% ≈ 0 with steals.
- Cost: 1 extra call (`MatchupsRollup`). On/off, Base Totals and hustle are shared.

## Speed

| Stat | Source | Min sample | Since |
|---|---|---|---|
| Offensive rebounds (season) | Base `Totals` → `OREB` | — | 1996-97 |
| Loose balls recovered (season) | `LeagueHustleStatsPlayer`, `per_mode_time='Totals'` → `LOOSE_BALLS_RECOVERED` | — | 2016-17 |
| Total transition points (season) | `SynergyPlayTypes`, `player_or_team_abbreviation='P'`, `play_type_nullable='Transition'`, `type_grouping_nullable='offensive'` → `PTS` (missing = <10 transition possessions → 0) | — | 2012-13 |
| Dribbles per touch (season) | `LeagueDashPtStats`, `player_or_team='Player'`, `pt_measure_type='Possessions'`, `per_mode_simple='Totals'` → `AVG_DRIB_PER_TOUCH` | — (stable even under 1,000 touches) | 2013-14 |

Notes:
- **None of these track measured speed:** per-36 correlations with tracked average speed (`AVG_SPEED`, used in v1) are −0.08 (OREB), 0.17 (loose balls), 0.00 (transition points), 0.02 (dribbles per touch). Speed here would mean hustle/activity and open-court scoring rather than how fast a player moves. If measured speed matters, `AVG_SPEED`, drives, and dunk `playerLateralSpeed` are in the catalog.
- **Offensive rebounds vs. dribbles per touch cancel out:** correlation **−0.58** (OREB tracks height at 0.62; dribbles per touch at −0.68). Bigs score high on one and low on the other, so the composite compresses toward the middle (the reason screen assists were dropped from Sp. Attack). Transition points also run opposite to OREB (−0.34).
- **Dribbles per touch:** measures ball dominance/handling style. Year-to-year 0.92, and 0.90 even for players under 1,000 touches (qualified minimum is 515 touches), so no minimum is needed. Leaders: Jayson Tatum 5.75, Brandon Williams 5.39, Payton Pritchard 5.22; lowest: Robert Williams III 0.20, Gobert 0.22, Poeltl 0.25. Same call also returns `TOUCHES`, `TIME_OF_POSS`, `AVG_SEC_PER_TOUCH`, `FRONT_CT_TOUCHES`, paint/post/elbow touches.
- **Transition points:** Synergy `PTS` is from transition possessions the player finished (correlates 0.94 with fast-break points `PTS_FB`, the one-call alternative from Base `Misc`, available since 1996-97). Leaders: Maxey 485, Jaylen Brown 461, Alexander-Walker 451.
- **Leaders:** OREB Clingan 347, Gobert 299, Diabaté 273; loose balls Dyson Daniels 77, VJ Edgecombe 77, Gillespie 70.
- **Per-36:** OREB, loose balls and transition points are volume stats; consider per-36 to avoid overlapping with HP.
- Cost: 2 extra calls (Possessions tracking, Synergy transition). Base Totals and hustle are shared.

## Minimum samples

Only rate and percentage stats need one. Counting stats (minutes, points, dunks, rebounds, blocks, steals, contests, deflections, 3PM, AST−TOV, loose balls, transition points) are covered by the 500-minute filter.

**Method (verified 2026-11-08, 2024-25 and 2025-26 qualified players):** for percentage stats, the minimum is the *stabilization point*: the number of attempts where a player's percentage is half real skill and half luck. It's computed as `p(1−p) / true-talent variance`, where true-talent variance is how much more players vary than random chance alone would produce. Checked against year-to-year correlation above vs. below the threshold. Net ratings and dribbles per touch don't fit that formula, so they were checked by year-to-year correlation across sample-size bins.

| Stat | Sample measure | Stabilizes at | Min sample | Qualified nulled (2025-26) | Year-to-year above / below |
|---|---|---|---|---|---|
| 2-point FG% | 2PA | ~67 (59–75) | 70 | 13 of 378 | 0.66 / 0.21 |
| Interior defensive FG% | `FGA_LT_06` | ~57 (54–59) | 60 | 20 of 378 | 0.74 / 0.23 |
| Matchup FG% guarding guards | `MATCHUP_FGA` (G rows) | ~850 (683–1,030); nobody reaches it | 100 (floor only) | 9 of 378 | 0.32 overall |
| Net offensive rating | on-court minutes | — | 1,000 (optional) | 99 of 378 | 0.45 (1,500+) / 0.22 (<1,000) |
| Net defensive rating | on-court minutes | — | none | 0 | flat (0.33–0.39) |
| Dribbles per touch | `TOUCHES` | — | none | 0 | 0.90+ at every size |

## Season availability

First season each stat has complete data (verified 2026-11-08 by probing each endpoint backward). Base stats and the shot chart were tested at 1996-97, the first season stats.nba.com serves.

| First full season | Stats | Notes |
|---|---|---|
| 1996-97 | Minutes, games, PPG, 2PT FG%, dunks, DREB, BLK, 3PM, AST−TOV, STL, OREB | Shot chart dunk labels exist in 1996-97 (1,554 dunks in Nov 1996). |
| 2007-08 | Net offensive / defensive rating | `TeamPlayerOnOffSummary` returns 0 rows for 2006-07 and earlier. |
| 2012-13 | Transition points (Synergy) | 2011-12 and earlier return 0 rows. Fast-break points (`PTS_FB`, Base `Misc`) go back to 1996-97 as a substitute. |
| 2013-14 | Interior defensive FG%, dribbles per touch | Player tracking starts 2013-14 (2012-13 returns 0 rows). |
| 2016-17 | Shots contested, deflections, loose balls recovered | Hustle stats: 2015-16 is partial (147 players), 2014-15 and earlier empty. |
| **2017-18** | **Matchup FG% guarding guards** | 2016-17 is a fragment (291 defenders, median 60 possessions vs. ~3,150 in 2017-18). |

**Limiting stat: matchup FG% guarding guards → the full plan runs back to 2017-18.** Earlier seasons need substitutions:
- **2016-17:** drop matchup FG% guarding guards (Sp. Defense would have net defensive rating, steals, deflections).
- **2013-14 to 2015-16:** also drop shots contested, deflections and loose balls recovered (hustle).
- **2012-13 and earlier:** also lose interior defensive FG% and dribbles per touch; before 2012-13, use `PTS_FB` for transition points; before 2007-08, no net ratings.

Shortened seasons affect counting stats and the 500-minute filter: 2011-12 (66 games), 2019-20 (65–75), 2020-21 (72). Per-36 rates or ranking players within each season handles this.

## Standardization

How each raw stat is put on a common scale before it's combined into a composite (decided 2026-11-09).

1. **Population:** qualified players only (500+ total minutes). Means and standard deviations are computed over them, per season, so bench players don't drag the averages.
2. **Scale: plain z-score for every input:** `z = (x − mean) / sd`. No min-max. Every input ends on the same scale, so a composite weight means the same thing for each input.
3. **Direction:** flip the sign (`z → −z`) for stats where lower is better: interior defensive FG%, net defensive rating, matchup FG% guarding guards. (v1 used `1 − x` on min-max values.)
4. **Cap at ±3:** clip each input's z to [−3, 3] before weighting, so one extreme value (e.g. Clingan's 1,038 contests, z > 5) can't dominate a composite. This does the outlier work a log transform would otherwise be needed for.
5. **No log transforms by default.** A log is not a neutral cleanup: it stretches differences among low values and compresses high ones. Example (2025-26): logging dunks and PPG moves Jalen Brunson from the 75th to the 37th percentile in Attack, because his 0 dunks go from z −0.82 to −1.99 and his 26.0 PPG from +2.34 to +1.82. A log is applied only as a deliberate per-stat choice when differences at the low end should matter as much as at the top, with the reason recorded here. Currently: none.
6. **Composites:** weighted average of the capped z-scores. Composites are not re-standardized, because the next step uses only their order.
7. **Mapping to Pokémon stats:** unchanged from v1. Rank each composite among qualified players (percentile), then take the Pokémon stat value at that percentile of the Pokémon distribution for that stat.

Evidence (2025-26, equal weights): plain z vs. log-then-z vs. rank-based normal scores rank players almost identically (rank correlation 0.975–1.00 per composite; median player moves 0–3 percentiles). The choice mainly affects individual players with lopsided inputs, which is why logs are opt-in.

Still to decide: weights per composite, and how a null input (below its minimum sample) affects its composite: re-weight the remaining inputs, or impute z = 0 (league average).

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
- **Nulls from minimum samples:** decide how a null input affects its composite (e.g. average the remaining inputs with re-normalized weights).
- **Opposing inputs:** OREB vs. dribbles per touch (Speed) pull in opposite directions by position, compressing that composite.
- **Redundant inputs:** steals vs. deflections (0.89), blocks vs. contests (0.82).
- **Lower-is-better stats:** interior defensive FG%, net defensive rating and matchup FG% guarding guards must be inverted (sign flip after z-scoring; see [Standardization](#standardization)).