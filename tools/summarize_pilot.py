from __future__ import annotations

import argparse
import json
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="voice_agent.db")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as db:
        try:
            rows = db.execute("SELECT resolved,confusing,rating FROM feedback").fetchall()
        except sqlite3.OperationalError:
            rows = []
    print(json.dumps({"pilot_status": "NOT EXECUTED" if not rows else "human-run pilot feedback",
                      "feedback_count": len(rows),
                      "resolved_count": sum(bool(row[0]) for row in rows),
                      "confusing_count": sum(bool(row[1]) for row in rows),
                      "mean_rating": sum(row[2] for row in rows) / len(rows) if rows else None}, indent=2))


if __name__ == "__main__":
    main()
