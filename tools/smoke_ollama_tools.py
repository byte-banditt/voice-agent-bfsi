from __future__ import annotations

import argparse
import asyncio
import json

from app.providers import OllamaLLM


TOOLS = [{"type": "function", "function": {
    "name": "get_loan_status",
    "description": "Look up an invented demo loan after identity verification.",
    "parameters": {"type": "object", "properties": {"loan_id": {"type": "string"}}, "required": ["loan_id"]},
}}]


async def run(model: str, base_url: str) -> dict[str, object]:
    provider = OllamaLLM(model=model, base_url=base_url, think=False)
    return await provider.chat_with_tools("Call get_loan_status for loan-demo-1. Do not invent a status.", TOOLS)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.model, args.base_url)), indent=2))


if __name__ == "__main__":
    main()
