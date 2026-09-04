"""devkit logwatch — scan a log file for errors and summarize them (plain or AI-assisted)."""
import os
import re
from collections import Counter
from pathlib import Path

ERROR_PATTERN = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|Exception|Traceback|panic:|FAIL(ED)?)\b", re.IGNORECASE
)

# Patterns for common secret shapes that shouldn't leave the machine.
# Deliberately conservative (over-redact rather than under-redact).
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|secret|token|password|passwd|auth)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9\-_.]+"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),                  # generic "sk-" style API keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                      # AWS access key IDs
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),            # GitHub tokens
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWTs
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),              # email addresses
]


def _redact(text: str) -> str:
    """Strip likely secrets/PII from text before it leaves the machine."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


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


def _ai_summary(error_lines: list[str], assume_yes: bool, model: str) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    import requests

    raw_excerpt = "\n".join(error_lines[-200:])
    excerpt = _redact(raw_excerpt)

    if excerpt != raw_excerpt and not assume_yes:
        print("Some lines look like they contain secrets/credentials/emails.")
        print("These have been redacted, but the remaining log text will still be")
        print("sent to Groq's API (api.groq.com).")
        reply = input("Continue? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            return "(AI summary skipped by user.)"
    elif not assume_yes:
        print("Log excerpt will be sent to Groq's API (api.groq.com) for summarization.")
        reply = input("Continue? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            return "(AI summary skipped by user.)"

    prompt = (
        "Here are error/warning lines pulled from a log file. In under 150 words, "
        "explain in plain English what's likely going wrong and suggest what to check first:\n\n"
        f"{excerpt}"
    )
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        return choices[0].get("message", {}).get("content") or None
    except requests.exceptions.Timeout:
        return "(AI summary failed: request timed out)"
    except requests.exceptions.ConnectionError:
        return "(AI summary failed: could not connect to api.groq.com)"
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        detail = ""
        if e.response is not None:
            try:
                detail = f" ({e.response.json().get('error', {}).get('message', '')})"
            except ValueError:
                pass
        return f"(AI summary failed: Groq API returned HTTP {status}{detail})"
    except (ValueError, KeyError):
        return "(AI summary failed: unexpected response format)"


def run(
    log_path: str,
    lines: int,
    use_ai: bool,
    assume_yes: bool = False,
    model: str = "llama-3.3-70b-versatile",
) -> None:
    path = Path(log_path)
    if not path.exists():
        print(f"No such file: {log_path}")
        return

    recent = _tail_lines(path, lines)
    error_lines = [l for l in recent if ERROR_PATTERN.search(l)]

    print(f"Scanned last {len(recent)} line(s) of {log_path}")
    print()

    if use_ai:
        ai_result = _ai_summary(error_lines, assume_yes, model)
        if ai_result:
            print("AI summary:")
            print(ai_result)
            return
        print("(No GROQ_API_KEY set, call failed, or was skipped — falling back to plain summary)")
        print()

    print(_plain_summary(error_lines))
