import struct


def pcm16_resample(pcm: bytes, source_rate: int, target_rate: int) -> bytes:
    """Linear interpolation for mono signed 16-bit PCM; handles any positive rates."""
    if source_rate <= 0 or target_rate <= 0:
        raise ValueError("sample rates must be positive")
    if len(pcm) % 2:
        raise ValueError("PCM16 byte length must be even")
    samples = [item[0] for item in struct.iter_unpack("<h", pcm)]
    if source_rate == target_rate or len(samples) < 2:
        return pcm
    count = max(1, round(len(samples) * target_rate / source_rate))
    output: list[int] = []
    for index in range(count):
        position = index * source_rate / target_rate
        left = min(int(position), len(samples) - 1)
        right = min(left + 1, len(samples) - 1)
        fraction = position - int(position)
        value = round(samples[left] * (1 - fraction) + samples[right] * fraction)
        output.append(max(-32768, min(32767, value)))
    return struct.pack(f"<{len(output)}h", *output)


def mulaw_to_pcm16(encoded: bytes) -> bytes:
    """Decode G.711 mu-law bytes to little-endian signed PCM16."""
    decoded = []
    for value in encoded:
        value = ~value & 0xFF
        sign = value & 0x80
        exponent = (value >> 4) & 0x07
        mantissa = value & 0x0F
        magnitude = ((mantissa << 3) + 0x84) << exponent
        sample = magnitude - 0x84
        decoded.append(-sample if sign else sample)
    return struct.pack(f"<{len(decoded)}h", *decoded)


def pcm16_to_mulaw(pcm: bytes) -> bytes:
    """Encode little-endian signed PCM16 samples as G.711 mu-law."""
    if len(pcm) % 2:
        raise ValueError("PCM16 byte length must be even")
    encoded = bytearray()
    for (sample,) in struct.iter_unpack("<h", pcm):
        sign = 0x80 if sample < 0 else 0
        magnitude = min(abs(sample), 32635) + 0x84
        exponent = 7
        mask = 0x4000
        while exponent > 0 and not magnitude & mask:
            exponent -= 1
            mask >>= 1
        mantissa = (magnitude >> (exponent + 3)) & 0x0F
        encoded.append(~(sign | (exponent << 4) | mantissa) & 0xFF)
    return bytes(encoded)
