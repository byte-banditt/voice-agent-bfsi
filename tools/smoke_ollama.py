from __future__ import annotations

import argparse
import asyncio

from app.providers import OllamaLLM


async def run(model: str, base_url: str) -> str:
    provider = OllamaLLM(model=model, base_url=base_url, think=False)
    return "".join([part async for part in provider.stream_reply("Say: I can help with an EMI reminder." )])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args()
    print(asyncio.run(run(args.model, args.base_url)))


if __name__ == "__main__":
    main()
