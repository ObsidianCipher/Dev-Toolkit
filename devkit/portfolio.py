"""devkit portfolio — pull a GitHub user's repos, rank them, and format a portfolio blurb."""
import os
from urllib.parse import quote

import requests


def _fetch_repos(username: str) -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "devkit-cli"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    safe_username = quote(username, safe="")
    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{safe_username}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=15,
        )
        if resp.status_code == 403 and "rate limit" in resp.text.lower() and not token:
            raise requests.RequestException(
                "GitHub rate limit hit for unauthenticated requests. "
                "Set a GITHUB_TOKEN env var to raise the limit."
            )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
        if len(batch) < 100:
            break
    return repos


def _rank(repos: list[dict], by: str) -> list[dict]:
    if by == "stars":
        return sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
    return sorted(repos, key=lambda r: r.get("pushed_at", ""), reverse=True)


def _format_blurb(repos: list[dict], limit: int) -> str:
    lines = ["## Portfolio", ""]
    for r in repos[:limit]:
        name = r["name"]
        desc = r.get("description") or "No description provided."
        stars = r.get("stargazers_count", 0)
        lang = r.get("language") or "—"
        url = r.get("html_url", "")
        lines.append(f"### [{name}]({url})")
        lines.append(f"{desc}")
        lines.append(f"_{lang} · ★ {stars}_")
        lines.append("")
    return "\n".join(lines)


def run(username: str, by: str, limit: int, exclude_forks: bool) -> None:
    try:
        repos = _fetch_repos(username)
    except requests.RequestException as e:
        print(f"Failed to fetch repos for '{username}': {e}")
        return

    if exclude_forks:
        repos = [r for r in repos if not r.get("fork")]

    if not repos:
        print(f"No repos found for '{username}'.")
        return

    ranked = _rank(repos, by)
    print(_format_blurb(ranked, limit))
