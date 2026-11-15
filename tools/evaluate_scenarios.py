from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    scenarios = json.loads(Path("scenarios/scenarios.json").read_text(encoding="utf-8"))
    results = [{**scenario, "status": "NOT EXECUTED",
                "reason": "end-to-end conversation/tool/telephony flow is not wired"}
               for scenario in scenarios]
    print(json.dumps({"classification": "SYNTHETIC scenario catalogue", "results": results,
                      "pass_rate": "NOT EXECUTED"}, indent=2))


if __name__ == "__main__":
    main()
