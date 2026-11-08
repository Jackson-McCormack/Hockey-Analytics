from collections import defaultdict, deque
import pandas as pd

IN = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/games.csv"
OUT = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/features.csv"

FORM_GAMES = 10    # games in the recent-form window
MAX_REST = 5        # cap rest days (first game of a season, long breaks)
ELO_START = 1000
ELO_K = 12      # how fast Elo reacts to one result
ELO_HOME = 23       # home-ice bonus in Elo points
ELO_CARRY = 0.8     # share of Elo kept between seasons (rest regresses to 1500)

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
        row["elo_prob"] = 1 / (1 + 10 ** ((elo[g.away] - elo[g.home] - ELO_HOME) / 400))
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

import numpy as np

tune = out[out["season"].isin(["2022", "2023"])]   # never look at 2024 here
y = tune["home_win"]
p = tune["elo_prob"].clip(0.001, 0.999)
base = y.mean()

def log_loss(y, p):
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

print(len(out), "games with features")
print(out[["home_b2b", "away_b2b"]].mean())
print(out.groupby("home_b2b")["home_win"].mean())

print(f"\nSettings: K={ELO_K}  HOME={ELO_HOME}  CARRY={ELO_CARRY}")
print(f"Games scored: {len(tune)} (2022-23 + 2023-24)\n")
print(f"{'':22}{'Elo':>8}{'Baseline':>10}")
print(f"{'Log loss (lower=better)':22}{log_loss(y, p):8.4f}{log_loss(y, np.full(len(y), base)):10.4f}")
print(f"{'Brier (lower=better)':22}{np.mean((p - y) ** 2):8.4f}{np.mean((base - y) ** 2):10.4f}")
print(f"{'Accuracy':22}{np.mean((p > 0.5) == y):8.1%}{max(base, 1 - base):10.1%}")

print("\nCalibration (does 60% mean 60%?)")
bins = pd.cut(p, [0, 0.4, 0.5, 0.6, 0.7, 1])
cal = tune.assign(p=p).groupby(bins, observed=True).agg(games=("home_win", "size"),
                                                        predicted=("p", "mean"),
                                                        actual=("home_win", "mean"))
print(cal.round(3))