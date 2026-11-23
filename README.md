# project_MJB1: NBA over/under hit rates

Search any NBA player, pick a stat (points, rebounds, assists, 3-pointers, steals, blocks, Pts+Reb+Ast),
type the line you want, and see how many of his last 5/10/15/20 games, and his games against a chosen opponent,
went over or under it.

## How it works

- `scripts/fetch_data.py` downloads every player's game logs for the last 3 seasons from NBA.com (through the `nba_api` package).
- It checks the data before saving (see "Accuracy"). If any check fails, the old file stays in place.
- `docs/` is the website. It only reads `docs/data/games.json`.
- `.github/workflows/daily.yml` runs the script every day at 6pm Brisbane time and commits the new data.

## Set it up (about 10 minutes)

1. Create a free GitHub account and a new **public** repository. Upload everything in this folder to it.
2. In the repository go to Settings > Pages. Set the source to the `main` branch and the `/docs` folder. Your site address appears there.
3. Open the Actions tab, choose "Update NBA data" and press "Run workflow". When it finishes (a few minutes), open your site.

From then on it updates itself every day.

## Accuracy: what is checked

- For every team in every game, the points of all listed players must add up to the team's score.
  This catches missing players, missing games and partial downloads. If one game fails, nothing is published.
- Stats must be whole numbers, not negative, with no missing values, and no game may be dated in the future.
- The new data may not hold fewer games than the previous run (a sign of an incomplete download).
- Only games where the player played (minutes above zero) count. Over means strictly above the line, under means strictly below, and an exact match is a push.
- The calculations are covered by tests (`python -m unittest discover -s tests` and `node tests/logic.test.js`), which also run before every update.

## Known limits

- **NBA.com sometimes blocks cloud servers.** GitHub's runners may time out against stats.nba.com. If the workflow fails
  with a timeout, either add a proxy address as a repository secret named `NBA_PROXY` (Settings > Secrets and variables > Actions),
  or run the script on your own computer: `pip install -r requirements.txt`, then `python scripts/fetch_data.py` once a day
  (Task Scheduler on Windows, cron or launchd on Mac), and upload the new `docs/data` file.
- Players traded very recently show their old team until they play a game for the new one.
- News is not included yet.
- GitHub pauses scheduled runs on repositories with no activity for 60 days. Open the Actions tab and re-enable it if that happens.

## Running it locally

```
python scripts/fetch_data.py
cd docs && python -m http.server 8000
```
Then open http://localhost:8000 (opening index.html directly won't work because browsers block file loading).
