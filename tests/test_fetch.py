import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fetch_data as fd  # noqa: E402


def prow(pid, name, tid, abbr, gid, date, matchup, mn, pts, reb=0, ast=0, fg3m=0, stl=0, blk=0):
    return dict(PLAYER_ID=pid, PLAYER_NAME=name, TEAM_ID=tid, TEAM_ABBREVIATION=abbr, GAME_ID=gid,
                GAME_DATE=date, MATCHUP=matchup, MIN=mn, PTS=pts, REB=reb, AST=ast, FG3M=fg3m, STL=stl, BLK=blk)


def trow(tid, gid, pts):
    return dict(TEAM_ID=tid, GAME_ID=gid, PTS=pts)


def sample():
    players = [
        prow(1, "Ann A", 10, "AAA", "001", "2026-11-20", "AAA vs. BBB", 30, 20, 5, 3, 2, 1, 0),
        prow(2, "Bo A", 10, "AAA", "001", "2026-11-20", "AAA vs. BBB", 20, 10, 2, 1, 0, 0, 1),
        prow(3, "Cy A", 10, "AAA", "001", "2026-11-20", "AAA vs. BBB", 0, 0),  # did not play
        prow(4, "Di B", 20, "BBB", "001", "2026-11-20", "BBB @ AAA", 35, 25, 9, 4, 3, 2, 2),
        prow(1, "Ann A", 10, "AAA", "002", "2026-11-22", "AAA @ BBB", 28, 18, 7, 6, 1, 0, 0),
        prow(2, "Bo A", 10, "AAA", "002", "2026-11-22", "AAA @ BBB", 22, 12, 3, 2, 1, 1, 0),
        prow(4, "Di B", 20, "BBB", "002", "2026-11-22", "BBB vs. AAA", 33, 22, 8, 5, 2, 1, 1),
    ]
    teams = [trow(10, "001", 30), trow(20, "001", 25), trow(10, "002", 30), trow(20, "002", 22)]
    return players, teams


class Parsing(unittest.TestCase):
    def test_matchup(self):
        self.assertEqual(fd.parse_matchup("LAL vs. BOS"), ("LAL", "BOS", True))
        self.assertEqual(fd.parse_matchup("LAL @ BOS"), ("LAL", "BOS", False))
        with self.assertRaises(ValueError):
            fd.parse_matchup("nonsense")

    def test_dates(self):
        self.assertEqual(fd.parse_date("2026-11-20").isoformat(), "2026-11-20")
        self.assertEqual(fd.parse_date("2026-11-20T00:00:00").isoformat(), "2026-11-20")
        self.assertEqual(fd.parse_date("NOV 20, 2026").isoformat(), "2026-11-20")

    def test_seasons(self):
        self.assertEqual(fd.season_label(dt.date(2026, 11, 23)), "2026-27")
        self.assertEqual(fd.season_label(dt.date(2027, 3, 1)), "2026-27")
        self.assertEqual(fd.season_label(dt.date(2026, 1, 5)), "2025-26")
        self.assertEqual(fd.recent_seasons(dt.date(2026, 11, 23)), ["2026-27", "2025-26", "2024-25"])


class Dataset(unittest.TestCase):
    def test_build(self):
        players, teams = sample()
        data, problems = fd.build_dataset(players, teams)
        self.assertEqual(problems, [])
        self.assertNotIn(3, data)  # never played
        self.assertEqual(data[1]["g"][0], ["2026-11-22", "BBB", 0, 18, 7, 6, 1, 0, 0, 28, 0])
        self.assertEqual(data[1]["g"][1], ["2026-11-20", "BBB", 1, 20, 5, 3, 2, 1, 0, 30, 0])
        self.assertEqual(data[4]["t"], "BBB")
        self.assertEqual(sum(len(p["g"]) for p in data.values()), 6)

    def test_points_mismatch_is_caught(self):
        players, teams = sample()
        teams[0] = trow(10, "001", 31)  # team scored 1 more than its players
        data, problems = fd.build_dataset(players, teams)
        self.assertEqual(len(problems), 1)
        errs = fd.check_dataset(data, problems, None, ["s"], dt.date(2026, 11, 23))
        self.assertTrue(errs)

    def test_missing_player_row_is_caught(self):
        players, teams = sample()
        players = [r for r in players if not (r["PLAYER_ID"] == 2 and r["GAME_ID"] == "002")]
        _, problems = fd.build_dataset(players, teams)
        self.assertEqual(len(problems), 1)

    def test_duplicates_ignored(self):
        players, teams = sample()
        data, problems = fd.build_dataset(players + [players[0]], teams)
        self.assertEqual(problems, [])
        self.assertEqual(len(data[1]["g"]), 2)

    def test_missing_stat_raises(self):
        players, teams = sample()
        players[0]["STL"] = None
        with self.assertRaises(ValueError):
            fd.build_dataset(players, teams)

    def test_clean_data_passes(self):
        players, teams = sample()
        data, problems = fd.build_dataset(players, teams)
        self.assertEqual(fd.check_dataset(data, problems, None, ["s"], dt.date(2026, 11, 23)), [])

    def test_future_date_and_drop(self):
        players, teams = sample()
        data, problems = fd.build_dataset(players, teams)
        self.assertTrue(fd.check_dataset(data, problems, None, ["s"], dt.date(2026, 11, 1)))
        old = {"seasons": ["s"], "games": 1000}
        self.assertTrue(fd.check_dataset(data, problems, old, ["s"], dt.date(2026, 11, 23)))
        old = {"seasons": ["other"], "games": 1000}  # season rolled over: no drop rule
        self.assertEqual(fd.check_dataset(data, problems, old, ["s"], dt.date(2026, 11, 23)), [])


if __name__ == "__main__":
    unittest.main()
