import json, os, time
from datetime import date, timedelta
import requests

SEASONS = [
    (date(2022, 10, 1), date(2023, 4, 20)),
    (date(2023, 10, 1), date(2024, 4, 20)),
    (date(2024, 10, 1), date(2025, 4, 20)),
]
rawFiles = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/raw2"

os.makedirs(rawFiles, exist_ok=True)

for start, end in SEASONS:
    day = start
    while day <= end:
        path = f"{rawFiles}/{day}.json"
        if not os.path.exists(path):
            resp = requests.get(f"https://api-web.nhle.com/v1/score/{day}")
            resp.raise_for_status()
            with open(path, "w") as f:
                json.dump(resp.json(), f)
            print("saved", day)
            time.sleep(0.5)
        day += timedelta(days=1)