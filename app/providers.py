from __future__ import annotations

import asyncio
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
        return text.encode("utf-8")
