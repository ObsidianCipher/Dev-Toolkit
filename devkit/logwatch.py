"""devkit logwatch — scan a log file for errors and summarize them (plain or AI-assisted)."""
import os
import re
from collections import Counter
from pathlib import Path

ERROR_PATTERN = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|Exception|Traceback|panic:|FAIL(ED)?)\b", re.IGNORECASE
)


def _tail_lines(path: Path, n: int) -> list[str]:
    with path.open(errors="ignore") as f:
        lines = f.readlines()
    return lines[-n:]


def _plain_summary(error_lines: list[str]) -> str:
    if not error_lines:
        return "No error-like lines found in the scanned window."

    counts = Counter()
    for line in error_lines:
        m = ERROR_PATTERN.search(line)
        if m:
            counts[m.group(1).upper()] += 1

    parts = [f"{len(error_lines)} error-like line(s) found."]
    if counts:
        breakdown = ", ".join(f"{k}: {v}" for k, v in counts.most_common())
        parts.append(f"Breakdown — {breakdown}")
    parts.append("\nSample lines:")
    for line in error_lines[:10]:
        parts.append(f"  {line.rstrip()}")
    if len(error_lines) > 10:
        parts.append(f"  ... and {len(error_lines) - 10} more")
    return "\n".join(parts)


def _ai_summary(error_lines: list[str]) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    import requests

    excerpt = "\n".join(error_lines[-200:])
    prompt = (
        "Here are error/warning lines pulled from a log file. In under 150 words, "
        "explain in plain English what's likely going wrong and suggest what to check first:\n\n"
        f"{excerpt}"
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(text_blocks) if text_blocks else None
    except Exception as e:  # noqa: BLE001
        return f"(AI summary failed: {e})"


def run(log_path: str, lines: int, use_ai: bool) -> None:
    path = Path(log_path)
    if not path.exists():
        print(f"No such file: {log_path}")
        return

    recent = _tail_lines(path, lines)
    error_lines = [l for l in recent if ERROR_PATTERN.search(l)]

    print(f"Scanned last {len(recent)} line(s) of {log_path}")
    print()

    if use_ai:
        ai_result = _ai_summary(error_lines)
        if ai_result:
            print("AI summary:")
            print(ai_result)
            return
        print("(No ANTHROPIC_API_KEY set or AI call failed — falling back to plain summary)")
        print()

    print(_plain_summary(error_lines))
