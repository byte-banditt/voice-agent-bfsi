from __future__ import annotations

import argparse
import asyncio
import csv
import wave
from pathlib import Path

from app.providers import FasterWhisperASR


async def transcribe(manifest: Path, output: Path, model: str, device: str, compute_type: str, beam_size: int) -> None:
    provider = FasterWhisperASR(model, device, compute_type, beam_size)
    with manifest.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    hypotheses = []
    for row in rows:
        with wave.open(row["path"], "rb") as audio:
            if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 16000:
                raise ValueError(f"{row['path']}: expected mono 16 kHz PCM16 WAV")
            pcm = audio.readframes(audio.getnframes())
        prediction = await provider.transcribe(pcm, 16000)
        hypotheses.append({"path": row["path"], "hypothesis": prediction})
    with output.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=("path", "hypothesis"))
        writer.writeheader()
        writer.writerows(hypotheses)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="base.en")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(transcribe(args.manifest, args.output, args.model, args.device, args.compute_type, args.beam_size))
    print(f"hypotheses_written={args.output} model={args.model} device={args.device} compute_type={args.compute_type} beam_size={args.beam_size}")


if __name__ == "__main__":
    main()
