#!/usr/bin/env python3
"""AoS Match Outcome Predictor

Lightweight exploratory script to train a logistic regression model for
Age of Sigmar (AoS) match outcomes based on recent rolling performance,
player streak, factions, opponent, and basic recency features.

Differences vs earlier scratch version:
- Uses psycopg (v3) instead of psycopg2 when available.
- Validates table existence before querying.
- Adds configurable test size & random seed.
- Provides richer docstring, future TODO roadmap.

Table expected: aos_matches(ts, season, player, opponent, faction, opponent_faction, outcome, score, meta)
Outcome values: 'win' | 'loss' | 'draw'

Example:
    ./scripts/aos_predict.py \
        --dsn "postgresql://user:pass@localhost:5432/mydb" \
        --schema pii \
        --player SOME_PLAYER_ID \
        --window 12 \
        --test-size 0.25

Future TODOs:
- [ ] Serialize trained pipeline (joblib) via --out flag.
- [ ] Expose coefficients / odds ratios (--show-coefs).
- [ ] Add calibration curve & Brier score.
- [ ] Add opponent rolling stats + matchup interaction features.
- [ ] Optional time-decay weighting for older matches.
- [ ] Fallback to heuristic prior if insufficient history.
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Tuple, Dict, Any

# Prefer psycopg v3; fallback to psycopg2 if needed
try:  # pragma: no cover - import guard
    import psycopg  # type: ignore
    _PSYCOPG2 = False
except Exception:  # pragma: no cover
    import psycopg2 as psycopg  # type: ignore
    _PSYCOPG2 = True

import numpy as np  # type: ignore
import pandas as pd  # type: ignore
from sklearn.compose import ColumnTransformer  # type: ignore
from sklearn.linear_model import LogisticRegression  # type: ignore
from sklearn.metrics import accuracy_score, roc_auc_score  # type: ignore
from sklearn.model_selection import train_test_split  # type: ignore
from sklearn.pipeline import Pipeline  # type: ignore
from sklearn.preprocessing import OneHotEncoder  # type: ignore


def load_matches(dsn: str, player: Optional[str], schema: Optional[str]) -> pd.DataFrame:
    """Load matches from Postgres and guard against missing table."""
    # Connection context manager differs slightly across psycopg versions
    with psycopg.connect(dsn) as conn:  # type: ignore[attr-defined]
        with conn.cursor() as cur:  # type: ignore[attr-defined]
            if schema:
                # Use parameter when psycopg2, else simple f-string (search_path is not user provided multiple elements)
                if _PSYCOPG2:
                    cur.execute("SET search_path=%s,public", (schema,))
                else:
                    cur.execute(f"SET search_path={schema},public")
            cur.execute("SELECT to_regclass('aos_matches')")
            reg = cur.fetchone()
            if not reg or (isinstance(reg, tuple) and reg[0] is None):
                print("[aos-predict] table aos_matches not found in search_path.", file=sys.stderr)
                return pd.DataFrame()
            base = (
                "SELECT ts, season, player, opponent, faction, opponent_faction, outcome, score, meta FROM aos_matches"
            )
            if player:
                base += " WHERE player=%s"
            base += " ORDER BY ts ASC"
            cur.execute(base, (player,) if player else None)
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
    return pd.DataFrame(rows, columns=cols)


def build_features(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """Construct rolling + streak + recency derived features.

    window: number of prior games to aggregate (per player) for rolling stats.
    """
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["is_win"] = (df["outcome"] == "win").astype(int)
    df["is_loss"] = (df["outcome"] == "loss").astype(int)
    df.sort_values(["player", "ts"], inplace=True)

    def add_roll(g: pd.DataFrame) -> pd.DataFrame:
        g["roll_wins"] = g["is_win"].rolling(window, min_periods=1).sum().shift(1)
        g["roll_games"] = g["is_win"].rolling(window, min_periods=1).count().shift(1)
        g["roll_winrate"] = (g["roll_wins"] / g["roll_games"]).fillna(0.5)
        streak_vals = []
        streak = 0
        for w, l in zip(g["is_win"], g["is_loss"]):
            if w == 1:
                streak = streak + 1 if streak >= 0 else 1
            elif l == 1:
                streak = streak - 1 if streak <= 0 else -1
            else:
                streak = 0
            streak_vals.append(streak)
        g["streak"] = pd.Series(streak_vals, index=g.index).shift(1).fillna(0)
        return g

    df = df.groupby("player", group_keys=False).apply(add_roll)  # type: ignore[call-overload]
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
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
    feat_df["roll_winrate"].fillna(0.5, inplace=True)
    feat_df["streak"].fillna(0, inplace=True)
    feat_df["recency_days"].fillna(7.0, inplace=True)
    feat_df["y"] = y
    feat_df.dropna(inplace=True)
    return feat_df


def train_and_eval(feat_df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
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
    pipe = Pipeline([("pre", pre), ("clf", clf)])
    # Only stratify if both classes present
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
    ap = argparse.ArgumentParser(description="Train simple AoS match outcome model")
    ap.add_argument("--dsn", required=True, help="PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/db")
    ap.add_argument("--player", help="Optional player filter to model only one player")
    ap.add_argument("--schema", help="Optional schema to prepend to search_path (e.g., pii)")
    ap.add_argument("--window", type=int, default=10, help="Rolling window size (default: 10)")
    ap.add_argument("--test-size", type=float, default=0.2, help="Holdout fraction (default: 0.2)")
    ap.add_argument("--random-state", type=int, default=42, help="Random seed (default: 42)")
    args = ap.parse_args()

    df = load_matches(args.dsn, args.player, args.schema)
    if df.empty:
        print("[aos-predict] No matches found.")
        return
    feat = build_features(df, window=args.window)
    if feat.empty:
        print("[aos-predict] Feature frame empty after construction.")
        return
    _, metrics = train_and_eval(feat, test_size=args.test_size, random_state=args.random_state)
    print(f"[aos-predict] metrics: {metrics}")

    # TODO: add --out model.joblib for persistence; provide coefficient dump option.


if __name__ == "__main__":  # pragma: no cover
    main()
