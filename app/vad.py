from __future__ import annotations

import os


class WebRTCVAD:
    """Frame-based WebRTC VAD for mono PCM16 at 16 kHz."""

    def __init__(self, aggressiveness: int | None = None, frame_ms: int | None = None) -> None:
        self.aggressiveness = int(os.getenv("VAD_AGGRESSIVENESS", "2")) if aggressiveness is None else aggressiveness
        self.frame_ms = int(os.getenv("VAD_FRAME_MS", "20")) if frame_ms is None else frame_ms
        if self.aggressiveness not in range(4):
            raise ValueError("VAD_AGGRESSIVENESS must be between 0 and 3")
        if self.frame_ms not in {10, 20, 30}:
            raise ValueError("VAD_FRAME_MS must be 10, 20, or 30")
        import webrtcvad

        self._vad = webrtcvad.Vad(self.aggressiveness)
        self.frame_bytes = 16000 * self.frame_ms // 1000 * 2

    def is_speech(self, frame: bytes) -> bool:
        if len(frame) != self.frame_bytes:
            raise ValueError(f"VAD frame must contain exactly {self.frame_bytes} bytes")
        return self._vad.is_speech(frame, 16000)


class EndpointingBuffer:
    """Accumulate speech and finish after configured consecutive silence frames."""

    def __init__(self, vad: WebRTCVAD, speech_frames: int | None = None, silence_frames: int | None = None) -> None:
        self.vad = vad
        self.speech_frames = int(os.getenv("VAD_SPEECH_FRAMES", "2")) if speech_frames is None else speech_frames
        self.silence_frames = int(os.getenv("VAD_SILENCE_FRAMES", "15")) if silence_frames is None else silence_frames
        self._partial = bytearray()
        self._speech = bytearray()
        self._voiced = 0
        self._silent = 0

    def feed(self, pcm16: bytes) -> list[bytes]:
        self._partial.extend(pcm16)
        utterances: list[bytes] = []
        frame_size = self.vad.frame_bytes
        while len(self._partial) >= frame_size:
            frame = bytes(self._partial[:frame_size])
            del self._partial[:frame_size]
            if self.vad.is_speech(frame):
                self._voiced += 1
                self._silent = 0
                if self._voiced >= self.speech_frames:
                    self._speech.extend(frame)
            elif self._voiced >= self.speech_frames:
                self._silent += 1
                self._speech.extend(frame)
                if self._silent >= self.silence_frames:
                    utterances.append(bytes(self._speech))
                    self.reset()
        return utterances

    def reset(self) -> None:
        self._partial.clear()
        self._speech.clear()
        self._voiced = 0
        self._silent = 0
