import struct

import pytest

from app.audio import mulaw_to_pcm16, pcm16_resample
from app.vad import EndpointingBuffer
from app.vad import EndpointingBuffer


def test_resample_doubles_sample_count_for_8khz_to_16khz() -> None:
    pcm = struct.pack("<2h", 0, 1000)
    result = pcm16_resample(pcm, 8000, 16000)
    assert len(result) == 8
    assert struct.unpack("<4h", result) == (0, 500, 1000, 1000)


def test_resample_validates_input() -> None:
    with pytest.raises(ValueError):
        pcm16_resample(b"x", 8000, 16000)
    with pytest.raises(ValueError):
        pcm16_resample(b"\x00\x00", 0, 16000)


def test_mulaw_decode_returns_pcm16() -> None:
    assert len(mulaw_to_pcm16(b"\xff\x7f")) == 4


def test_endpointing_waits_for_speech_then_silence_timeout() -> None:
    class VAD:
        frame_bytes = 4

        def __init__(self):
            self.frames = 0

        def is_speech(self, frame):
            self.frames += 1
            return self.frames <= 2

    endpoint = EndpointingBuffer(VAD(), speech_frames=2, silence_frames=3)
    assert endpoint.feed(b"\x01" * 20) == [b"\x01" * 16]


def test_endpointing_waits_for_speech_then_silence_timeout() -> None:
    class VAD:
        frame_bytes = 4

        def __init__(self):
            self.frames = 0

        def is_speech(self, frame):
            self.frames += 1
            return self.frames <= 2

    endpoint = EndpointingBuffer(VAD(), speech_frames=2, silence_frames=3)
    assert endpoint.feed(b"\x01" * 20) == [bytes([1]) * 16]
