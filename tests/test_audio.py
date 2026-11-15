import struct

import pytest

from app.audio import mulaw_to_pcm16, pcm16_resample


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
