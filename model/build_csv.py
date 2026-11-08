import json, os
import pandas as pd

rawData = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/raw/"

csvOutput = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/games.csv"

rows = []

for filename in sorted(os.listdir(rawData)):
    if not filename.endswith(".json"):
        continue
    with open(os.path.join(rawData, filename)) as f:
        data = json.load(f)
    
    for game in data.get("games", []):
        if game["gameType"] != 2:                  # 2 = regular season
            continue
        if game["gameState"] not in ("OFF", "FINAL"):
            continue
        rows.append({
            "game_id": game["id"],
            "date": filename.replace(".json", ""),
            "home": game["homeTeam"]["abbrev"],
            "away": game["awayTeam"]["abbrev"],
            "home_goals": game["homeTeam"]["score"],
            "away_goals": game["awayTeam"]["score"],
            "outcome": game["gameOutcome"]["lastPeriodType"],  # REG / OT / SO
        })

df = pd.DataFrame(rows).drop_duplicates("game_id")
df = df.replace({"home": {"ARI": "UTA"}, "away": {"ARI": "UTA"}})
df["home_win"] = (df["home_goals"] > df["away_goals"]).astype(int)
df.to_csv(csvOutput, index=False)
print(len(df), "games saved")

df = pd.read_csv(csvOutput)
print(len(df))                                   # expect ~3,936
print(df["outcome"].value_counts())              # mostly REG, some OT/SO
print(df["home_win"].mean())                     # expect ~0.52–0.55
games_per_team = pd.concat([df["home"], df["away"]]).value_counts()
print(games_per_team.describe())                 # expect 246 each (82 × 3)