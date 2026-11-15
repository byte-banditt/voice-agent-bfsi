from __future__ import annotations

import argparse
import json
import statistics
import time

import httpx


def benchmark(base_url: str, model: str, repeats: int) -> dict[str, object]:
    rows = []
    for think in (True, False):
        measurements = []
        for _ in range(repeats):
            start = time.perf_counter()
            response = httpx.post(
                f"{base_url.rstrip('/')}/api/chat",
                json={"model": model, "think": think, "stream": False,
                      "messages": [{"role": "user", "content": "In one short sentence, say you can help with an EMI reminder."}]},
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            elapsed = time.perf_counter() - start
            measurements.append({"wall_seconds": elapsed,
                                 "total_duration_ns": payload.get("total_duration"),
                                 "prompt_eval_count": payload.get("prompt_eval_count"),
                                 "eval_count": payload.get("eval_count"),
                                 "done_reason": payload.get("done_reason")})
        rows.append({"think": think, "runs": measurements,
                     "median_wall_seconds": statistics.median(row["wall_seconds"] for row in measurements)})
    return {"model": model, "results": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen3:0.6b")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    print(json.dumps(benchmark(args.base_url, args.model, args.repeats), indent=2))


if __name__ == "__main__":
    main()
