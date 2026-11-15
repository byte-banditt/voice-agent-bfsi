from __future__ import annotations

import argparse
import csv
import json
import wave
from pathlib import Path


def inspect_manifest(manifest: Path) -> list[dict[str, object]]:
    rows = []
    with manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            path = Path(row["path"])
            if not path.is_file():
                raise FileNotFoundError(path)
            with wave.open(str(path), "rb") as audio:
                if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
                    raise ValueError(f"{path}: expected mono PCM16 WAV")
                rows.append({"path": str(path), "reference": row["reference"],
                             "language": row["language"], "split": row["split"],
                             "sample_rate": audio.getframerate(), "frames": audio.getnframes(),
                             "data_type": "SYNTHETIC" if row.get("data_type") == "SYNTHETIC" else "REAL"})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-real", type=int, default=40)
    args = parser.parse_args()
    rows = inspect_manifest(args.manifest)
    real_count = sum(row["data_type"] == "REAL" for row in rows)
    if real_count < args.minimum_real:
        raise SystemExit(f"NOT EXECUTED: found {real_count} REAL utterances; need at least {args.minimum_real}")
    args.output.write_text(json.dumps({"utterances": rows}, indent=2) + "\n", encoding="utf-8")
    print(f"validated={len(rows)} real={real_count} output={args.output}")


if __name__ == "__main__":
    main()
