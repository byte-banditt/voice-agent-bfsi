from __future__ import annotations

import json
import urllib.request


def main() -> None:
    packages = (
        "fastapi", "uvicorn", "prometheus-client", "httpx", "python-dotenv",
        "pytest", "numpy", "faster-whisper", "piper-tts", "presidio-analyzer",
        "presidio-anonymizer", "jiwer", "PyYAML", "websockets", "av",
    )
    for name in packages:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json") as response:
            data = json.load(response)
        print(f"{name}=={data['info']['version']}")


if __name__ == "__main__":
    main()
