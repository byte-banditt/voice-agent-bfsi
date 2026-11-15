from prometheus_client import Counter, Histogram

STAGE_SECONDS = Histogram(
    "voice_agent_stage_seconds",
    "Elapsed seconds by call processing stage",
    ("stage",),
)

TOOL_SECONDS = Histogram(
    "voice_agent_tool_seconds",
    "Elapsed seconds by backend tool",
    ("tool",),
)
TOOL_CALLS = Counter(
    "voice_agent_tool_calls_total",
    "Backend tool calls by outcome",
    ("tool", "outcome"),
)
