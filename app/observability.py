from __future__ import annotations

import json
import math
import sqlite3
import time
import uuid
import statistics
from pathlib import Path
from typing import Any

from app.guardrails import redact_pii


class CallStore:
    def __init__(self, path: str | Path = "voice_agent.db") -> None:
        self.path = str(path)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, created REAL, trace TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, call_id TEXT, resolved INTEGER, confusing INTEGER, rating INTEGER, free_text TEXT)")

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save_trace(self, trace: dict[str, Any]) -> str:
        call_id = str(trace.get("call_id") or uuid.uuid4())
        safe = dict(trace)
        safe["call_id"] = call_id
        if "transcript" in safe:
            safe["transcript"] = redact_pii(str(safe["transcript"]))
        for tool_call in safe.get("tool_calls", []):
            if not isinstance(tool_call, dict):
                continue
            arguments = tool_call.get("arguments")
            if isinstance(arguments, dict):
                tool_call["arguments"] = {"redacted": True, "field_names": sorted(arguments)}
            result = tool_call.get("result")
            if isinstance(result, dict):
                if tool_call.get("name") in {"get_customer", "get_loan_status", "create_payment_link"}:
                    tool_call["result"] = {"redacted": True, "success": "error" not in result}
                else:
                    tool_call["result"] = {
                        key: ("[REDACTED]" if key.casefold() in {"dob", "phone_last4", "phone", "customer_id", "requested_at", "name"} else value)
                        for key, value in result.items()
                    }
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO calls VALUES (?,?,?)", (call_id, time.time(), json.dumps(safe)))
        return call_id

    def add_feedback(self, call_id: str, resolved: bool, confusing: bool, rating: int, free_text: str) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")
        with self.connect() as db:
            db.execute("INSERT INTO feedback(call_id,resolved,confusing,rating,free_text) VALUES (?,?,?,?,?)",
                       (call_id, resolved, confusing, rating, redact_pii(free_text)))

    def list_calls(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT trace FROM calls ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def summary(self) -> dict[str, Any]:
        calls = self.list_calls()
        stages: dict[str, list[float]] = {}
        failures: dict[str, int] = {}
        prompts: dict[str, int] = {}
        prompt_tool_success: dict[str, list[int]] = {}
        prompt_stages: dict[str, dict[str, list[float]]] = {}
        guardrail_events: dict[str, int] = {}
        tool_latencies: dict[str, list[float]] = {}
        tool_errors: dict[str, int] = {}
        tool_total = 0
        tool_success = 0
        for call in calls:
            for stage, value in call.get("stage_seconds", {}).items():
                stages.setdefault(stage, []).append(float(value))
                prompt_stages.setdefault(str(call.get("prompt_version", "unknown")), {}).setdefault(stage, []).append(float(value))
            for failure in call.get("errors", []):
                failures[str(failure)] = failures.get(str(failure), 0) + 1
            version = str(call.get("prompt_version", "unknown"))
            prompts[version] = prompts.get(version, 0) + 1
            for item in call.get("tool_calls", []):
                tool_total += 1
                succeeded = isinstance(item.get("result"), dict) and "error" not in item["result"]
                tool_success += int(succeeded)
                counts = prompt_tool_success.setdefault(version, [0, 0])
                counts[0] += int(succeeded)
                counts[1] += 1
                if isinstance(item.get("duration_seconds"), (int, float)):
                    tool_latencies.setdefault(str(item.get("name", "unknown")), []).append(float(item["duration_seconds"]))
                if item.get("error_category"):
                    category = str(item["error_category"])
                    tool_errors[category] = tool_errors.get(category, 0) + 1
            for event in call.get("guardrail_events", []):
                guardrail_events[str(event)] = guardrail_events.get(str(event), 0) + 1
        percentiles = {
            name: {"p50": statistics.median(values), "p95": sorted(values)[min(len(values) - 1, math.ceil(len(values) * 0.95) - 1)]}
            for name, values in stages.items() if values
        }
        return {"call_count": len(calls), "stage_percentiles_seconds": percentiles,
                "failure_tags": failures, "calls_by_prompt_version": prompts,
                "tool_success_rate": tool_success / tool_total if tool_total else None,
                "tool_calls": {"success": tool_success, "total": tool_total},
                "tool_errors": tool_errors,
                "tool_latency_percentiles_seconds": {
                    name: {"p50": statistics.median(values), "p95": sorted(values)[min(len(values) - 1, math.ceil(len(values) * 0.95) - 1)]}
                    for name, values in tool_latencies.items() if values
                },
                "guardrail_events": guardrail_events,
                "prompt_versions": {
                    version: {
                        "calls": count,
                        "tool_success_rate": (prompt_tool_success[version][0] / prompt_tool_success[version][1]
                                              if version in prompt_tool_success else None),
                        "stage_percentiles_seconds": {
                            stage: {"p50": statistics.median(values), "p95": sorted(values)[min(len(values) - 1, math.ceil(len(values) * 0.95) - 1)]}
                            for stage, values in prompt_stages.get(version, {}).items() if values
                        },
                    } for version, count in prompts.items()
                }}
