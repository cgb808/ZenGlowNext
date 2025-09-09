#!/usr/bin/env python3
"""
AoS player stats report. Refreshes materialized view if missing.

Usage:
  ./scripts/aos_stats_report.py --dsn $DATABASE_URL_TS [--player <name>]

This script assumes the presence of:
- Materialized view: public.aos_player_stats (player, games, wins, losses, draws, win_rate)
- Optional helper function: refresh_aos_stats() to (re)build the MV
"""
import argparse
from typing import Optional
import psycopg2


def report(dsn: str, player: Optional[str] = None) -> None:
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            # Check if MV exists; if not, try to refresh/build via helper
            cur.execute("SELECT to_regclass('public.aos_player_stats')")
            reg = cur.fetchone()
            if not reg or (isinstance(reg, tuple) and reg[0] is None):
                try:
                    print("[stats] Refreshing materialized view via refresh_aos_stats()...")
                    cur.execute("SELECT refresh_aos_stats()")
                    conn.commit()
                except Exception as e:
                    print(f"[stats] Could not refresh MV: {e}")
            if player:
                cur.execute(
                    "SELECT player, games, wins, losses, draws, win_rate FROM aos_player_stats WHERE player = %s",
                    (player,),
                )
            else:
                cur.execute(
                    "SELECT player, games, wins, losses, draws, win_rate FROM aos_player_stats ORDER BY win_rate DESC NULLS LAST, games DESC LIMIT 20"
                )
            rows = cur.fetchall()
            print("player\tgames\twins\tlosses\tdraws\twin_rate%")
            for r in rows:
                print("\t".join(str(x) for x in r))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=True)
    ap.add_argument("--player")
    args = ap.parse_args()
    report(args.dsn, args.player)


if __name__ == "__main__":
    main()
