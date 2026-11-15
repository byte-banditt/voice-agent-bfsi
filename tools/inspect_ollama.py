from __future__ import annotations

import argparse
import json
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen3:0.6b")
    args = parser.parse_args()
    with urllib.request.urlopen(f"{args.base_url.rstrip('/')}/api/tags") as response:
        payload = json.load(response)
    found = [model for model in payload["models"] if model["name"] == args.model]
    print(json.dumps([{"name": model["name"], "size": model["size"], "details": model["details"]}
                      for model in found], indent=2))


if __name__ == "__main__":
    main()
