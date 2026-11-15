from __future__ import annotations

import argparse

from faster_whisper import WhisperModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe faster-whisper file-path input")
    parser.add_argument("audio")
    parser.add_argument("--model", default="base.en")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    args = parser.parse_args()
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments, _ = model.transcribe(args.audio, beam_size=args.beam_size)
    print(" ".join(segment.text.strip() for segment in segments).strip())


if __name__ == "__main__":
    main()
