from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    scenarios = json.loads(Path("scenarios/scenarios.json").read_text(encoding="utf-8"))
    if len(scenarios) < 20:
        raise SystemExit("scenario catalogue is below the requested minimum")
    results = [{**scenario, "status": "NOT EXECUTED",
                "reason": "scenario runner with deterministic provider/CRM fixtures is not implemented"}
               for scenario in scenarios]
    print(json.dumps({"classification": "SYNTHETIC scenario catalogue", "results": results,
                      "pass_rate": "NOT EXECUTED"}, indent=2))


if __name__ == "__main__":
    main()
