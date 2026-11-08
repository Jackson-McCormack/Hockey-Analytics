

import requests

url = "https://api-web.nhle.com/v1/score/2026-11-06"

data = requests.get(url).json()

currentdate = data["currentDate"]

for game in data["games"]:
    home = game["homeTeam"]
    away = game["awayTeam"]
    print(f' {home["abbrev"]} {home ["score"]} - {away["score"]} {away["abbrev"]} ')


# print(game.keys())

TMR = game["gameOutcome"]

print(TMR)