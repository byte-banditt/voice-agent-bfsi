from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from jiwer import wer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--hypotheses", required=True, type=Path)
    args = parser.parse_args()
    with args.manifest.open(newline="", encoding="utf-8") as source:
        references = list(csv.DictReader(source))
    with args.hypotheses.open(newline="", encoding="utf-8") as source:
        hypotheses = {row["path"]: row["hypothesis"] for row in csv.DictReader(source)}
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in references:
        if row["path"] not in hypotheses:
            raise ValueError(f"missing hypothesis for {row['path']}")
        kind = "SYNTHETIC" if row.get("data_type") == "SYNTHETIC" else "REAL"
        if kind == "SYNTHETIC" and row.get("variant"):
            kind += "_" + row["variant"].upper()
        groups[kind].append((row["reference"], hypotheses[row["path"]]))
    for kind in ("REAL", "SYNTHETIC_CLEAN", "SYNTHETIC_NOISY"):
        pairs = groups[kind]
        if pairs:
            print(f"{kind} utterances={len(pairs)} WER={wer([x[0] for x in pairs],[x[1] for x in pairs]):.6f}")
        else:
            print(f"{kind} NOT EXECUTED: no rows")


if __name__ == "__main__":
    main()
