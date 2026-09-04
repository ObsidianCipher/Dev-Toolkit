"""devkit — a small multi-tool CLI for indie devs.

Subcommands:
  snap       Snapshot the current state of a git repo (diffs, branch, recent commits).
  envcheck   Compare code's env var usage against .env / .env.example.
  deadcode   Flag Python functions/classes that look unreferenced.
  logwatch   Scan a log file for errors, optionally summarized via Claude.
  portfolio  Pull a GitHub user's repos into a ranked portfolio blurb.
"""
import click

from devkit import snap as snap_mod
from devkit import envcheck as envcheck_mod
from devkit import deadcode as deadcode_mod
from devkit import logwatch as logwatch_mod
from devkit import portfolio as portfolio_mod


@click.group()
@click.version_option(package_name="devkit")
def cli():
    """devkit — snapshot, envcheck, deadcode, logwatch, and portfolio in one CLI."""


@cli.command()
@click.option("--path", "repo_path", default=".", help="Path to the git repo.")
@click.option("--json", "as_json", is_flag=True, help="Output JSON instead of markdown.")
@click.option("--output", "-o", default=None, help="Write output to a file instead of stdout.")
def snap(repo_path, as_json, output):
    """Summarize the current state of a git repo."""
    snap_mod.run(repo_path, as_json, output)


@cli.command()
@click.option("--path", "project_path", default=".", help="Path to the project.")
@click.option("--interactive", is_flag=True, help="Prompt for missing values and write .env.")
def envcheck(project_path, interactive):
    """Check for missing/unused environment variables."""
    envcheck_mod.run(project_path, interactive)


@cli.command()
@click.option("--path", "project_path", default=".", help="Path to the project.")
def deadcode(project_path):
    """Flag Python functions/classes that look unused (heuristic)."""
    deadcode_mod.run(project_path)


@cli.command()
@click.argument("log_path")
@click.option("--lines", "-n", default=500, help="How many trailing lines to scan.")
@click.option("--ai", "use_ai", is_flag=True, help="Summarize via Claude (needs ANTHROPIC_API_KEY).")
def logwatch(log_path, lines, use_ai):
    """Scan a log file for errors and summarize them."""
    logwatch_mod.run(log_path, lines, use_ai)


@cli.command()
@click.argument("username")
@click.option("--by", type=click.Choice(["stars", "recent"]), default="stars", help="Ranking key.")
@click.option("--limit", default=6, help="How many repos to include.")
@click.option("--exclude-forks", is_flag=True, help="Exclude forked repos.")
def portfolio(username, by, limit, exclude_forks):
    """Pull a GitHub user's repos into a ranked portfolio blurb."""
    portfolio_mod.run(username, by, limit, exclude_forks)


if __name__ == "__main__":
    cli()
