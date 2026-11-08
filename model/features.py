from collections import defaultdict, deque
import pandas as pd

IN = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/games.csv"
OUT = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/features.csv"

FORM_GAMES = 10     # games in the recent-form window
MAX_REST = 7        # cap rest days (first game of a season, long breaks)
ELO_START = 1500
ELO_K = 8           # how fast Elo reacts to one result
ELO_HOME = 50       # home-ice bonus in Elo points
ELO_CARRY = 0.7     # share of Elo kept between seasons (rest regresses to 1500)

df = pd.read_csv(IN, parse_dates=["date"])
df = df.sort_values(["date", "game_id"]).reset_index(drop=True)
df["season"] = df["game_id"].astype(str).str[:4]

last_date = {}
recent_gd = defaultdict(lambda: deque(maxlen=FORM_GAMES))
elo = defaultdict(lambda: ELO_START)
current_season = None
features = []

for g in df.itertuples():
    # new season: reset rest/form, pull Elo partway back to average
    if g.season != current_season:
        current_season = g.season
        last_date.clear()
        recent_gd.clear()
        for team in elo:
            elo[team] = ELO_CARRY * elo[team] + (1 - ELO_CARRY) * ELO_START

    row = {"game_id": g.game_id}

    # 1. record each team's state BEFORE this game
    for side, team in (("home", g.home), ("away", g.away)):
        if team in last_date:
            rest = min((g.date - last_date[team]).days - 1, MAX_REST)
        else:
            rest = MAX_REST
        row[f"{side}_rest"] = rest
        row[f"{side}_b2b"] = int(rest == 0)

        gds = recent_gd[team]
        row[f"{side}_gd10"] = sum(gds) / len(gds) if gds else 0.0
        row[f"{side}_elo"] = elo[team]

    features.append(row)

    # 2. only now update state with this game's result
    margin = g.home_goals - g.away_goals
    recent_gd[g.home].append(margin)
    recent_gd[g.away].append(-margin)
    last_date[g.home] = g.date
    last_date[g.away] = g.date

    expected_home = 1 / (1 + 10 ** ((elo[g.away] - elo[g.home] - ELO_HOME) / 400))
    change = ELO_K * (g.home_win - expected_home)
    elo[g.home] += change
    elo[g.away] -= change

feat = pd.DataFrame(features)
out = df.merge(feat, on="game_id")
out["rest_diff"] = out["home_rest"] - out["away_rest"]
out["gd10_diff"] = out["home_gd10"] - out["away_gd10"]
out["elo_diff"] = out["home_elo"] - out["away_elo"]
out.to_csv(OUT, index=False)

print(len(out), "games with features")
print(out[["home_b2b", "away_b2b"]].mean())
print(out.groupby("home_b2b")["home_win"].mean())
print(out.groupby(pd.cut(out["elo_diff"], [-200, -50, 0, 50, 200]))["home_win"].mean())