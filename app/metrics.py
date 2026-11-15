from prometheus_client import Histogram

STAGE_SECONDS = Histogram(
    "voice_agent_stage_seconds",
    "Elapsed seconds by call processing stage",
    ("stage",),
)
