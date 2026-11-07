"""Make one live nba_api call and summarize what actually comes back.

Usage:
  python probe.py <EndpointClass> [--season 2025-26] [--param key=value ...]
                  [--dataset N] [--raw-key KEY] [--show col1,col2] [--top COL] [--out file.csv]

Examples:
  python probe.py LeagueDashPtStats --season 2025-26 --param player_or_team=Player --param pt_measure_type=Drives
  python probe.py SynergyPlayTypes --season 2025-26 --param player_or_team_abbreviation=P --param play_type_nullable=Cut --param type_grouping_nullable=offensive --top POSS
  python probe.py DunkScoreLeaders --season 2025-26 --param player_id_nullable=0 --param team_id_nullable=0 --raw-key dunks --show playerVertical,hangTime
"""
import argparse
import difflib
import inspect
import sys

import pandas as pd
from nba_api.stats import endpoints

PLAYER_ID_COLS = ["PLAYER_ID", "playerId", "personId", "PERSON_ID", "CLOSE_DEF_PERSON_ID", "VS_PLAYER_ID"]
ROW_CAPS = {102400}  # response sizes observed to be silent truncation
NAME_COLS = ["PLAYER_NAME", "playerName", "PLAYER", "name", "TEAM_NAME", "teamName"]


def load_endpoint(name):
    cls = getattr(endpoints, name, None)
    if cls is None or not inspect.isclass(cls):
        candidates = [n for n in dir(endpoints) if inspect.isclass(getattr(endpoints, n))]
        close = difflib.get_close_matches(name, candidates, n=5, cutoff=0.4)
        sys.exit(f"Unknown endpoint {name!r}. Close matches: {close}")
    return cls


def build_kwargs(cls, args):
    sig = inspect.signature(cls.__init__).parameters
    kwargs = {}
    for p in args.param:
        if "=" not in p:
            sys.exit(f"--param must be key=value, got {p!r}")
        k, v = p.split("=", 1)
        if k not in sig:
            sys.exit(f"{cls.__name__} has no parameter {k!r}. Valid: {[n for n in sig if n != 'self']}")
        kwargs[k] = v
    if args.season:
        season_params = [n for n in sig if "season" in n and "type" not in n and "segment" not in n]
        if "season" in sig:
            kwargs.setdefault("season", args.season)
        elif season_params:
            kwargs.setdefault(season_params[0], args.season)
            print(f"note: passing season as {season_params[0]!r}")
        else:
            print(f"note: {cls.__name__} takes no season parameter; --season ignored")
    if "timeout" in sig:
        kwargs["timeout"] = 60
    return kwargs


def fix_duplicate_columns(df, nba_response):
    """Some endpoints (e.g. LeagueDashPlayerShotLocations) repeat FGM/FGA/FG_PCT once per zone,
    with the zone names in a second header row. Rename to '<zone> <col>'; else suffix duplicates."""
    if isinstance(df.columns, pd.MultiIndex) or any(isinstance(c, tuple) for c in df.columns):
        flat = [" ".join(str(p) for p in c if str(p).strip()) if isinstance(c, tuple) else str(c) for c in df.columns]
        df = df.set_axis(flat, axis=1)
    if not df.columns.duplicated().any():
        return df
    cols = list(df.columns)
    try:
        headers = nba_response.get_dict()["resultSets"]["headers"]
        top, bottom = headers[0], headers[-1]
        if len(bottom["columnNames"]) == len(cols):
            skip, span = top.get("columnsToSkip") or 0, top["columnSpan"]
            new = list(bottom["columnNames"])
            for i, group in enumerate(top["columnNames"]):
                for j in range(span):
                    k = skip + i * span + j
                    if k < len(new):
                        new[k] = f"{group} {new[k]}"
            if len(set(new)) == len(new):
                return df.set_axis(new, axis=1)
    except Exception:
        pass
    seen = {}
    new = []
    for c in cols:
        seen[c] = seen.get(c, -1) + 1
        new.append(f"{c}_{seen[c]}" if seen[c] else c)
    return df.set_axis(new, axis=1)


def fetch(cls, kwargs, args):
    """Return (frames: dict[str, DataFrame], source description)."""
    ep = cls(get_request=False, **kwargs)
    error = None
    try:
        ep.get_request()
    except Exception as e:  # nba_api often fails to parse responses that do contain data
        error = e

    if error is None and not args.raw_key:
        try:
            dfs = ep.get_data_frames()
            # Names in response order; expected_data's order can differ from the actual response
            try:
                names = list(ep.nba_response.get_data_sets().keys())
            except Exception:
                names = []
            if len(names) != len(dfs):
                names = [f"set{i}" for i in range(len(dfs))]
            dfs = [fix_duplicate_columns(df, ep.nba_response) for df in dfs]
            return {names[i] if i < len(names) else f"set{i}": df for i, df in enumerate(dfs)}, "nba_api parsed"
        except Exception as e:
            error = e

    if ep.nba_response is None:
        sys.exit(f"Request failed before any response: {error!r}")
    try:
        raw = ep.nba_response.get_dict()
    except ValueError:
        resp = ep.nba_response
        status = getattr(resp, "_status_code", "?")
        text = (resp.get_response() or "").strip()
        print(f"Response is not JSON (HTTP {status}); usually means no data for these parameters.")
        print(f"url: {resp.get_url()}")
        print(f"body (truncated): {text[:500]!r}")
        sys.exit(1)
    if error is not None:
        print(f"note: nba_api parsing failed ({type(error).__name__}: {error}); falling back to raw JSON")

    lists = {k: v for k, v in raw.items() if isinstance(v, list) and v and isinstance(v[0], dict)}
    if args.raw_key:
        if args.raw_key not in raw:
            sys.exit(f"--raw-key {args.raw_key!r} not in response. Top-level keys: {list(raw)}")
        return {args.raw_key: pd.DataFrame(raw[args.raw_key])}, "raw JSON"
    if lists:
        return {k: pd.DataFrame(v) for k, v in lists.items()}, "raw JSON"

    # Nothing tabular: probably an API error message (e.g. invalid parameter values)
    print("No tabular data in response. Raw response (truncated):")
    print(str(raw)[:1500])
    sys.exit(1)


def summarize(name, df, args, verbose):
    print(f"\n=== {name}: {len(df)} rows x {len(df.columns)} cols ===")
    if len(df) in ROW_CAPS:
        print(f"WARNING: {len(df)} rows is a known stats.nba.com row cap; data is probably truncated "
              "(not necessarily by date). Split the request, e.g. by month with date_from_nullable/date_to_nullable.")
    if df.empty:
        print("(empty: endpoint answered but returned no rows for these parameters)")
        return
    pid = next((c for c in PLAYER_ID_COLS if c in df.columns), None)
    if pid:
        print(f"unique {pid}: {df[pid].nunique()}")
    if not verbose:
        print("columns:", list(df.columns))
        return

    nulls = (df.isna().mean() * 100).round(1)
    print("columns (null %):")
    print("  " + ", ".join(f"{c} ({nulls[c]})" if nulls[c] else c for c in df.columns))

    show = [c.strip() for c in args.show.split(",")] if args.show else []
    missing = [c for c in show if c not in df.columns]
    if missing:
        print(f"note: --show columns not found: {missing}")
    show = [c for c in show if c in df.columns]
    if show:
        num = df[show].select_dtypes("number")
        if not num.empty:
            print("\nsummary of --show columns:")
            print(num.describe().round(3).to_string())

    label = [c for c in NAME_COLS if c in df.columns][:1]
    head_cols = list(dict.fromkeys(label + show)) or list(df.columns[:12])
    view = df
    if args.top:
        if args.top not in df.columns:
            print(f"note: --top column {args.top!r} not found")
        else:
            view = df.sort_values(args.top, ascending=False)
            head_cols = list(dict.fromkeys(head_cols + [args.top]))
    print("\nsample rows:")
    print(view[head_cols].head(8).to_string(index=False))


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("endpoint", help="nba_api endpoint class name, e.g. LeagueDashPtStats")
    ap.add_argument("--season", help="Season 'YYYY-YY'; mapped to the endpoint's season parameter")
    ap.add_argument("--param", action="append", default=[], help="Endpoint kwarg as key=value (repeatable)")
    ap.add_argument("--dataset", help="Only fully summarize this result set (index or name); default: the first")
    ap.add_argument("--raw-key", help="Skip nba_api parsing and read this top-level key of the raw JSON")
    ap.add_argument("--show", help="Comma-separated columns to describe and include in samples")
    ap.add_argument("--top", help="Sort sample rows by this column, descending")
    ap.add_argument("--out", help="Save the summarized result set to this CSV path")
    args = ap.parse_args()

    cls = load_endpoint(args.endpoint)
    kwargs = build_kwargs(cls, args)
    print(f"{cls.__name__}({', '.join(f'{k}={v!r}' for k, v in kwargs.items())})")

    frames, source = fetch(cls, kwargs, args)
    print(f"source: {source}; result sets: {list(frames)}")

    names = list(frames)
    target = names[0]
    if args.dataset is not None:
        target = names[int(args.dataset)] if args.dataset.isdigit() else args.dataset
        if target not in frames:
            sys.exit(f"--dataset {args.dataset!r} not found; result sets: {names}")
    for name in names:
        summarize(name, frames[name], args, verbose=(name == target))

    if args.out:
        frames[target].to_csv(args.out, index=False)
        print(f"\nsaved {target} to {args.out}")


if __name__ == "__main__":
    main()
