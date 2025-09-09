#!/usr/bin/env python3
"""
AoS match outcome predictor (edge). Timescale/PII-aware search_path.

- Reads matches from aos_matches (Timescale or Postgres table)
- Builds rolling features per player
- Trains logistic regression and prints AUC/accuracy

Usage:
  ./scripts/aos_predict.py --dsn $DATABASE_URL_TS [--player <name>] [--schema pii]

Env (optional):
  DATABASE_URL_TS / PII_DATABASE_URL_TS from 2x2 layout docs.
"""
import argparse
from typing import Optional
import sys

import numpy as np
import pandas as pd
import psycopg2
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def load_matches(dsn: str, player: Optional[str], schema: Optional[str]) -> pd.DataFrame:
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if schema:
                cur.execute("SET search_path=%s,public", (schema,))
            # Guard: table existence
            cur.execute("SELECT to_regclass('aos_matches')")
            reg = cur.fetchone()
            if not reg or (isinstance(reg, tuple) and reg[0] is None):
                print("[aos-predict] table aos_matches not found in search_path.", file=sys.stderr)
                return pd.DataFrame()
            q = (
                "SELECT ts, season, player, opponent, faction, opponent_faction, outcome, score, meta FROM aos_matches"
                + (" WHERE player=%s" if player else "")
                + " ORDER BY ts ASC"
            )
            if player:
                cur.execute(q, (player,))
            else:
                cur.execute(q)
            rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    cols = [
        "ts",
        "season",
        "player",
        "opponent",
        "faction",
        "opponent_faction",
        "outcome",
        "score",
        "meta",
    ]
    df = pd.DataFrame(rows, columns=cols)
    return df


def build_features(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    df = df.copy()
    df["is_win"] = (df["outcome"] == "win").astype(int)
    df["is_loss"] = (df["outcome"] == "loss").astype(int)
    # Rolling stats per player
    df.sort_values(["player", "ts"], inplace=True)

    def add_roll(g: pd.DataFrame) -> pd.DataFrame:
        g["roll_wins"] = g["is_win"].rolling(window, min_periods=1).sum().shift(1)
        g["roll_games"] = g["is_win"].rolling(window, min_periods=1).count().shift(1)
        g["roll_winrate"] = (g["roll_wins"] / g["roll_games"]).fillna(0.5)
        # simple streak: +1 on win, -1 on loss, reset on draw
        streak = []
        s = 0
        for w, l in zip(g["is_win"], g["is_loss"]):
            if w == 1:
                s = s + 1 if s >= 0 else 1
            elif l == 1:
                s = s - 1 if s <= 0 else -1
            else:
                s = 0
            streak.append(s)
        g["streak"] = pd.Series(streak, index=g.index).shift(1).fillna(0)
        return g

    df = df.groupby("player", group_keys=False).apply(add_roll)  # type: ignore[call-overload]
    # recency by player
    df["ts"] = pd.to_datetime(df["ts"])  # ensure datetime
    df["recency_days"] = (
        df.groupby("player")["ts"].diff().dt.total_seconds() / 86400.0
    ).fillna(7.0)

    y = df["is_win"].astype(int).values
    feat_df = df[
        [
            "season",
            "opponent",
            "faction",
            "opponent_faction",
            "roll_winrate",
            "streak",
            "recency_days",
        ]
    ].copy()
    feat_df["roll_winrate"] = feat_df["roll_winrate"].fillna(0.5)
    feat_df["streak"] = feat_df["streak"].fillna(0)
    feat_df["recency_days"] = feat_df["recency_days"].fillna(7.0)
    feat_df["y"] = y
    feat_df = feat_df.dropna()
    return pd.DataFrame(feat_df)


def train_and_eval(
    feat_df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
):
    if feat_df.empty:
        return None, {"auc": float("nan"), "accuracy": float("nan")}
    y = feat_df["y"].astype(int).values
    X = feat_df.drop(columns=["y"])
    cat_cols = ["season", "opponent", "faction", "opponent_faction"]
    num_cols = ["roll_winrate", "streak", "recency_days"]
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
            ("num", "passthrough", num_cols),
        ]
    )
    clf = LogisticRegression(max_iter=1000)
    pipe = Pipeline([( "pre", pre ), ( "clf", clf )])
    # guard stratify when only one class present
    if len(np.unique(y)) > 1:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
    pipe.fit(X_train, y_train)
    proba = pipe.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba) if len(np.unique(y_test)) > 1 else float("nan")
    acc = accuracy_score(y_test, (proba >= 0.5).astype(int))
    return pipe, {"auc": auc, "accuracy": acc}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True, help="Postgres/Timescale DSN")
    ap.add_argument("--player", help="Filter to a single player")
    ap.add_argument("--schema", help="search_path prefix, e.g., 'pii'")
    ap.add_argument("--window", type=int, default=10)
    args = ap.parse_args()

    df = load_matches(args.dsn, args.player, args.schema)
    if df.empty:
        print("[aos-predict] No matches found.")
        return
    feat = build_features(df, window=args.window)
    model, metrics = train_and_eval(feat)
    print(f"[aos-predict] metrics: {metrics}")


if __name__ == "__main__":
    main()
