from __future__ import annotations

import asyncio
import io
import json
import os
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


class ASRProvider(Protocol):
    async def transcribe(self, pcm16: bytes, sample_rate: int) -> str: ...


class LLMProvider(Protocol):
    async def stream_reply(self, transcript: str) -> AsyncIterator[str]: ...


class TTSProvider(Protocol):
    async def synthesize(self, text: str) -> bytes: ...


@dataclass(slots=True)
class FakeASR:
    transcript: str = "hello"

    async def transcribe(self, pcm16: bytes, sample_rate: int) -> str:
        if not pcm16:
            return ""
        return self.transcript


@dataclass(slots=True)
class FakeLLM:
    reply: str = "I can help with that."

    async def stream_reply(self, transcript: str) -> AsyncIterator[str]:
        for word in self.reply.split(" "):
            await asyncio.sleep(0)
            yield word + " "


@dataclass(slots=True)
class FakeTTS:
    async def synthesize(self, text: str) -> bytes:
        await asyncio.sleep(0)
        # Synthetic silence represents a deterministic audio payload in CI.
        return b"\x00\x00" * max(160, len(text) * 160)


class OllamaLLM:
    def __init__(self, model: str = "qwen3:0.6b", base_url: str = "http://localhost:11434", think: bool = False) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.think = think

    async def stream_reply(self, transcript: str) -> AsyncIterator[str]:
        import httpx

        payload = {"model": self.model, "think": self.think, "stream": True,
                   "messages": [{"role": "user", "content": transcript}]}
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break

    async def chat_with_tools(self, transcript: str, tools: list[dict[str, object]]) -> dict[str, object]:
        """Return Ollama's structured content/tool calls for the caller-owned executor."""
        import httpx

        payload = {"model": self.model, "think": self.think, "stream": False,
                   "messages": [{"role": "user", "content": transcript}], "tools": tools}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})
            return {"content": message.get("content", ""),
                    "tool_calls": message.get("tool_calls", [])}


class FasterWhisperASR:
    def __init__(self, model_name: str = "base.en", device: str = "cuda", compute_type: str = "float16") -> None:
        self.model_name, self.device, self.compute_type = model_name, device, compute_type
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
        return self._model

    async def transcribe(self, pcm16: bytes, sample_rate: int) -> str:
        if sample_rate != 16000:
            raise ValueError("FasterWhisperASR requires 16 kHz PCM")
        import numpy as np

        audio = np.frombuffer(pcm16, dtype="<i2").astype(np.float32) / 32768.0

        def run() -> str:
            segments, _ = self._get_model().transcribe(audio, beam_size=1)
            return " ".join(segment.text.strip() for segment in segments).strip()

        return await asyncio.to_thread(run)


class PiperTTS:
    def __init__(self, voice_path: str) -> None:
        self.voice_path = voice_path
        self._voice = None

    def _get_voice(self):
        if self._voice is None:
            if not self.voice_path:
                raise RuntimeError("PIPER_VOICE_PATH is not configured")
            from piper import PiperVoice

            self._voice = PiperVoice.load(self.voice_path)
        return self._voice

    async def synthesize(self, text: str) -> bytes:
        def run() -> bytes:
            output = io.BytesIO()
            with wave.open(output, "wb") as wav_file:
                self._get_voice().synthesize_wav(text, wav_file)
            with wave.open(io.BytesIO(output.getvalue()), "rb") as wav_file:
                if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                    raise ValueError("Piper voice must produce mono PCM16")
                sample_rate = wav_file.getframerate()
                pcm = wav_file.readframes(wav_file.getnframes())
            from app.audio import pcm16_resample

            return pcm16_resample(pcm, sample_rate, 16000)

        return await asyncio.to_thread(run)


def configured_providers() -> tuple[ASRProvider, LLMProvider, TTSProvider]:
    if os.getenv("VOICE_AGENT_REAL_PROVIDERS", "false").lower() != "true":
        return FakeASR(), FakeLLM(), FakeTTS()
    return (
        FasterWhisperASR(os.getenv("ASR_MODEL", "base.en"), os.getenv("ASR_DEVICE", "cuda"), os.getenv("ASR_COMPUTE_TYPE", "float16")),
        OllamaLLM(os.getenv("OLLAMA_MODEL", "qwen3:0.6b"), os.getenv("OLLAMA_URL", "http://localhost:11434"), think=False),
        PiperTTS(os.getenv("PIPER_VOICE_PATH", "")),
    )
