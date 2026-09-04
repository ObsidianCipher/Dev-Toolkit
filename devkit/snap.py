"""devkit snap — summarize the current state of a git repo as markdown/json."""
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd):
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False
        )
        return out.stdout.strip()
    except FileNotFoundError:
        return ""


def gather_snapshot(repo_path: str) -> dict:
    repo = str(Path(repo_path).resolve())

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    status = _run(["git", "status", "--porcelain"], repo)
    diff_stat = _run(["git", "diff", "--stat"], repo)
    staged_diff_stat = _run(["git", "diff", "--cached", "--stat"], repo)
    recent_commits = _run(
        ["git", "log", "-5", "--pretty=format:%h %ad %s", "--date=short"], repo
    )
    remotes = _run(["git", "remote", "-v"], repo)

    changed_files = [line[3:] for line in status.splitlines() if line]

    return {
        "repo_path": repo,
        "branch": branch or "(not a git repo?)",
        "changed_files": changed_files,
        "unstaged_diff_stat": diff_stat,
        "staged_diff_stat": staged_diff_stat,
        "recent_commits": recent_commits.splitlines() if recent_commits else [],
        "remotes": sorted(set(remotes.splitlines())) if remotes else [],
    }


def to_markdown(snap: dict) -> str:
    lines = [f"# Repo Snapshot — `{snap['branch']}`", ""]
    lines.append(f"**Path:** `{snap['repo_path']}`")
    lines.append("")

    lines.append("## Changed files")
    if snap["changed_files"]:
        for f in snap["changed_files"]:
            lines.append(f"- {f}")
    else:
        lines.append("_working tree clean_")
    lines.append("")

    if snap["unstaged_diff_stat"]:
        lines.append("## Unstaged diff stat")
        lines.append("```")
        lines.append(snap["unstaged_diff_stat"])
        lines.append("```")
        lines.append("")

    if snap["staged_diff_stat"]:
        lines.append("## Staged diff stat")
        lines.append("```")
        lines.append(snap["staged_diff_stat"])
        lines.append("```")
        lines.append("")

    lines.append("## Recent commits")
    if snap["recent_commits"]:
        for c in snap["recent_commits"]:
            lines.append(f"- {c}")
    else:
        lines.append("_no commits found_")
    lines.append("")

    if snap["remotes"]:
        lines.append("## Remotes")
        for r in snap["remotes"]:
            lines.append(f"- `{r}`")
        lines.append("")

    return "\n".join(lines)


def run(repo_path: str, as_json: bool, output: str | None) -> None:
    snap = gather_snapshot(repo_path)
    text = json.dumps(snap, indent=2) if as_json else to_markdown(snap)

    if output:
        Path(output).write_text(text)
        print(f"Snapshot written to {output}", file=sys.stderr)
    else:
        print(text)
