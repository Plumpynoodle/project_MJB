#!/usr/bin/env python3
"""Fetch NBA player game logs, check them, and write docs/data/games.json.

If any check fails the script exits with an error and leaves the previous
files untouched, so the site never shows half-updated numbers.
"""
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
SEASONS_BACK = 3
MIN_KEEP = 0.95  # new data may not hold fewer games than 95% of the old data

# ---------- seasons and parsing ----------

def season_label(today):
    start = today.year if today.month >= 10 else today.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def recent_seasons(today, n=SEASONS_BACK):
    start = int(season_label(today)[:4])
    return [f"{s}-{(s + 1) % 100:02d}" for s in range(start, start - n, -1)]


def parse_date(s):
    s = str(s)
    try:
        return dt.datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return dt.datetime.strptime(s, "%b %d, %Y").date()


def parse_matchup(m):
    """'LAL vs. BOS' = home game, 'LAL @ BOS' = away game -> (team, opponent, is_home)."""
    if " vs. " in m:
        a, b = m.split(" vs. ")
        return a.strip(), b.strip(), True
    if " @ " in m:
        a, b = m.split(" @ ")
        return a.strip(), b.strip(), False
    raise ValueError(f"Unreadable matchup: {m!r}")


def played(row):
    try:
        return float(row.get("MIN") or 0) > 0
    except (TypeError, ValueError):
        return False


def num(row, key):
    v = row.get(key)
    if v is None:
        raise ValueError(f"{key} missing for {row.get('PLAYER_NAME', row.get('TEAM_ID'))} {row.get('GAME_DATE', '')}")
    f = float(v)
    if f < 0 or f != int(f):
        raise ValueError(f"Bad {key} value {v!r}")
    return int(f)


# ---------- NBA.com ----------

def fetch_log(season, season_type, kind):
    """kind 'P' = one row per player per game, 'T' = one row per team per game."""
    from nba_api.stats.endpoints import leaguegamelog
    err = None
    for attempt in range(1, 5):
        try:
            ep = leaguegamelog.LeagueGameLog(
                season=season,
                season_type_all_star=season_type,
                player_or_team_abbreviation=kind,
                timeout=90,
                proxy=os.environ.get("NBA_PROXY") or None,
            )
            return next(iter(ep.get_normalized_dict().values()))
        except Exception as e:  # network errors, blocks, bad responses
            err = e
            time.sleep(5 * attempt)
    raise RuntimeError(f"NBA.com request failed for {season} {season_type} {kind}: {err}")


def build_dataset(player_rows, team_rows):
    """Returns (players, problems). Each game is
    [date, opponent, home 1/0, pts, reb, ast, 3pm, stl, blk, minutes, playoffs 1/0], newest first.
    Only games the player actually played in (minutes > 0) are kept."""
    team_pts = {(str(r["GAME_ID"]), r["TEAM_ID"]): num(r, "PTS") for r in team_rows}
    sums, seen, players = {}, set(), {}
    for r in player_rows:
        gid = str(r["GAME_ID"])
        pid = int(r["PLAYER_ID"])
        if (pid, gid) in seen:
            continue
        seen.add((pid, gid))
        pts = num(r, "PTS")
        key = (gid, r["TEAM_ID"])
        sums[key] = sums.get(key, 0) + pts
        if not played(r):
            continue
        team, opp, home = parse_matchup(r["MATCHUP"])
        if team != r["TEAM_ABBREVIATION"]:
            raise ValueError(f"Matchup {r['MATCHUP']!r} does not match team {r['TEAM_ABBREVIATION']!r}")
        date = parse_date(r["GAME_DATE"]).isoformat()
        rec = [date, opp, 1 if home else 0, pts, num(r, "REB"), num(r, "AST"), num(r, "FG3M"),
               num(r, "STL"), num(r, "BLK"), int(round(float(r["MIN"]))), 1 if r.get("_po") else 0]
        p = players.setdefault(pid, {"n": r["PLAYER_NAME"], "t": team, "_d": ""})
        p.setdefault("g", []).append(rec)
        if date >= p["_d"]:
            p["_d"], p["t"], p["n"] = date, team, r["PLAYER_NAME"]
    for p in players.values():
        p.pop("_d")
        p["g"].sort(key=lambda g: g[0], reverse=True)
    problems = []
    for key, total in team_pts.items():
        got = sums.get(key, 0)
        if got != total:
            problems.append(f"game {key[0]} team {key[1]}: players add up to {got}, team scored {total}")
    for key in sums:
        if key not in team_pts:
            problems.append(f"game {key[0]} team {key[1]}: no team row to check against")
    return players, problems


def check_dataset(players, problems, old_meta, seasons, today):
    errs = []
    if problems:
        errs.append(f"{len(problems)} team games where player points do not add up to the team score, e.g. {problems[:3]}")
    total = sum(len(p["g"]) for p in players.values())
    if total == 0:
        errs.append("no games found")
    if old_meta and old_meta.get("seasons") == seasons and total < old_meta.get("games", 0) * MIN_KEEP:
        errs.append(f"only {total} games, previously {old_meta['games']}: the response looks incomplete")
    limit = (today + dt.timedelta(days=1)).isoformat()
    for p in players.values():
        for g in p["g"]:
            if g[0] > limit:
                errs.append(f"{p['n']} has a game dated in the future ({g[0]})")
            if g[3] > 100 or min(g[3:9]) < 0:
                errs.append(f"{p['n']} has an impossible stat line on {g[0]}")
    return errs[:10]


# ---------- main ----------

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def main():
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    seasons = recent_seasons(today)
    prow, trow = [], []
    for season in seasons:
        for st, po in (("Regular Season", 0), ("Playoffs", 1)):
            try:
                p = fetch_log(season, st, "P")
                time.sleep(2)
                t = fetch_log(season, st, "T")
                time.sleep(2)
            except Exception as e:
                if po:
                    print(f"note: {season} {st} not available ({e})")
                    continue
                raise
            for r in p:
                r["_po"] = po
            prow += p
            trow += t
    players, problems = build_dataset(prow, trow)
    old = (read_json(DATA / "games.json") or {}).get("meta")
    errs = check_dataset(players, problems, old, seasons, today)
    if errs:
        print("DATA CHECK FAILED, keeping the previous files:")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    games = sum(len(p["g"]) for p in players.values())
    latest = max(g[0] for p in players.values() for g in p["g"])
    write_json(DATA / "games.json", {
        "meta": {"updated": now.isoformat(timespec="seconds"), "latest_game": latest,
                 "seasons": seasons, "players": len(players), "games": games},
        "players": {str(k): v for k, v in players.items()},
    })
    print(f"games.json: {len(players)} players, {games} games, latest game {latest}, all checks passed")


if __name__ == "__main__":
    main()
