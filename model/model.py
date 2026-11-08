## model that is trained on features.py, which got its features from downloaded csvs

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, brier_score_loss

IN = "/Users/jackson-mac/Documents/GitHub/Hockey-Analytics/model/features.csv"

FEATURES = ["elo_diff", "rest_diff", "gd10_diff", "home_b2b", "away_b2b"]
TRAIN_SEASONS = ["2022", "2023"]
TEST_SEASON = "2024"

df = pd.read_csv(IN, dtype={"season": str})
train = df[df["season"].isin(TRAIN_SEASONS)]
test = df[df["season"] == TEST_SEASON]
y_train, y_test = train["home_win"], test["home_win"]


def fit(cols):
    model = make_pipeline(StandardScaler(), LogisticRegression())
    model.fit(train[cols], y_train)
    return model, model.predict_proba(test[cols])[:, 1]


elo_only_model, p_elo_lr = fit(["elo_diff"])
full_model, p_full = fit(FEATURES)

results = {
    "Baseline (home win %)": np.full(len(test), y_train.mean()),
    "Raw Elo": test["elo_prob"].to_numpy(),
    "Logistic: Elo only": p_elo_lr,
    "Logistic: all features": p_full,
}

print(f"Train: {len(train)} games ({', '.join(TRAIN_SEASONS)})   Test: {len(test)} games ({TEST_SEASON})\n")
print(f"{'':26}{'Log loss':>10}{'Brier':>9}{'Accuracy':>10}")
for name, p in results.items():
    acc = np.mean((p > 0.5) == y_test)
    print(f"{name:26}{log_loss(y_test, p):10.4f}{brier_score_loss(y_test, p):9.4f}{acc:10.1%}")

print("\nWhat the full model learned (per 1 std dev change; + favours home team):")
coefs = full_model.named_steps["logisticregression"].coef_[0]
for name, c in sorted(zip(FEATURES, coefs), key=lambda x: -abs(x[1])):
    print(f"  {name:12}{c:+.3f}")

print("\nCalibration on test season (full model)")
bins = pd.cut(p_full, [0, 0.4, 0.5, 0.6, 0.7, 1])
cal = (test.assign(p=p_full)
           .groupby(bins, observed=True)
           .agg(games=("home_win", "size"), predicted=("p", "mean"), actual=("home_win", "mean")))
print(cal.round(3))