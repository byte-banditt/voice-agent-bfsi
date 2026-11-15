from __future__ import annotations

import argparse
import io
import csv
import random
import struct
import wave
from pathlib import Path

import wave

from piper import PiperVoice, SynthesisConfig

from app.audio import pcm16_resample

PHRASES = (
    "Hello, this is a reminder from Example Finance.",
    "May I speak with the account holder?",
    "Please verify your date of birth and registered phone number.",
    "Would you like me to repeat the payment date?",
    "I can arrange a callback with a human agent.",
    "Your identity check was not successful.",
    "I cannot discuss another person's account.",
    "Would you prefer to continue in English?",
    "Thank you, I will end the call now.",
    "I can help you check the loan status.",
)


def make_noisy(pcm: bytes, noise_scale: int, rng: random.Random) -> bytes:
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    mixed = [max(-32768, min(32767, sample + round(rng.gauss(0, noise_scale)))) for sample in samples]
    return struct.pack(f"<{len(mixed)}h", *mixed)


async def synthesize(voice: str, output: Path, noise_scale: int, seed: int) -> list[dict[str, str]]:
    import asyncio

    output.mkdir(parents=True, exist_ok=True)
    tts = PiperVoice.load(voice)
    config = SynthesisConfig(noise_scale=0.0, noise_w_scale=0.0)
    rng = random.Random(seed)
    rows = []
    for index, phrase in enumerate(PHRASES, start=1):
        output_wav = io.BytesIO()
        with wave.open(output_wav, "wb") as wav_file:
            tts.synthesize_wav(phrase, wav_file, syn_config=config)
        with wave.open(io.BytesIO(output_wav.getvalue()), "rb") as wav_file:
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise ValueError("Piper voice must produce mono PCM16")
            pcm = pcm16_resample(wav_file.readframes(wav_file.getnframes()), wav_file.getframerate(), 16000)
        for variant, samples in (("clean", pcm), ("noisy", make_noisy(pcm, noise_scale, rng))):
            path = output / f"utt-{index:02d}-{variant}.wav"
            with wave.open(str(path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(samples)
            rows.append({"path": str(path), "reference": phrase, "language": "en", "split": "synthetic",
                         "data_type": "SYNTHETIC", "variant": variant})
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as manifest:
        writer = csv.DictWriter(manifest, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local Piper speech and deterministic Gaussian-noise variants")
    parser.add_argument("--voice", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--noise-scale", type=int, default=250)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    if args.noise_scale < 0:
        parser.error("--noise-scale must be nonnegative")
    import asyncio

    rows = asyncio.run(synthesize(str(args.voice), args.output, args.noise_scale, args.seed))
    print(f"classification=SYNTHETIC utterances={len(rows)} clean={sum(x['variant']=='clean' for x in rows)} noisy={sum(x['variant']=='noisy' for x in rows)} gaussian_noise_scale={args.noise_scale} seed={args.seed} piper_noise_scale=0.0 piper_noise_w_scale=0.0 output={args.output}")


if __name__ == "__main__":
    main()
