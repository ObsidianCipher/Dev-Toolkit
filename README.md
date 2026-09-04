# devkit

A small multi-tool CLI for indie devs. One tool, five commands, no config files.

## Install

```bash
pip install -e .
```

This installs a `devkit` command on your PATH (via `pyproject.toml`'s entry point).

## Commands

### `devkit snap`
Summarize the current state of a git repo — branch, changed files, diff stats, and recent commits — as markdown (paste into a PR description) or JSON.

```bash
devkit snap                      # markdown to stdout
devkit snap --json               # JSON to stdout
devkit snap --path ../other-repo -o snapshot.md
```

### `devkit envcheck`
Scans your code (Python/JS/TS) for `os.environ` / `process.env` usage and your `.env.example`, then reports what's missing from your local `.env` — or what's set but unused.

```bash
devkit envcheck
devkit envcheck --interactive    # prompts for missing values, writes .env
```

### `devkit deadcode`
Heuristic scan for Python functions/classes defined but never referenced anywhere in the project. Not a full call-graph analysis — treat it as a lead, not a verdict.

```bash
devkit deadcode --path ./src
```

### `devkit logwatch`
Tails a log file, flags error-like lines (`ERROR`, `CRITICAL`, `Traceback`, `panic:`, etc.), and gives you a quick breakdown. With `--ai` and an `ANTHROPIC_API_KEY` set, it asks Claude for a plain-English read on what's likely wrong.

```bash
devkit logwatch app.log
devkit logwatch app.log -n 2000 --ai
```

### `devkit portfolio`
Pulls a GitHub user's public repos and formats a ranked markdown portfolio blurb — by stars or by recent activity.

```bash
devkit portfolio yourusername --by stars --limit 5 --exclude-forks
```

Set `GITHUB_TOKEN` to avoid GitHub's low unauthenticated rate limit.

## Notes

- `logwatch --ai` and `portfolio` make outbound API calls (Anthropic / GitHub respectively) — everything else runs fully offline.
- `deadcode` and `envcheck`'s code-scanning are intentionally simple (regex/AST based) to keep this a weekend build, not a static-analysis platform.
