from app.providers import FasterWhisperASR, FakeASR, FakeLLM, FakeTTS, configured_providers


def test_real_provider_defaults_to_multilingual_whisper(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_AGENT_REAL_PROVIDERS", "true")
    monkeypatch.delenv("ASR_MODEL", raising=False)

    asr, _, _ = configured_providers()

    assert isinstance(asr, FasterWhisperASR)
    assert asr.model_name == "base"


def test_fake_provider_default_remains_ci_safe(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_AGENT_REAL_PROVIDERS", "false")

    providers = configured_providers()

    assert isinstance(providers[0], FakeASR)
    assert isinstance(providers[1], FakeLLM)
    assert isinstance(providers[2], FakeTTS)
