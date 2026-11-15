from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


PACKAGES = (
    "fastapi", "uvicorn", "prometheus-client", "httpx", "python-dotenv", "pytest",
    "numpy", "faster-whisper", "piper-tts", "av", "presidio-analyzer",
    "presidio-anonymizer", "jiwer", "PyYAML", "websockets",
)


def main() -> None:
    for package in PACKAGES:
        try:
            print(f"{package}=={version(package)}")
        except PackageNotFoundError:
            print(f"{package}=NOT INSTALLED")


if __name__ == "__main__":
    main()
