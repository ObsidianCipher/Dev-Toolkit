"""devkit envcheck — find required env vars, compare to what's set, scaffold .env."""
import re
import sys
from pathlib import Path

ENV_REF_PATTERNS = [
    re.compile(r"os\.environ\[[\'\"](\w+)[\'\"]\]"),
    re.compile(r"os\.environ\.get\([\'\"](\w+)[\'\"]"),
    re.compile(r"os\.getenv\([\'\"](\w+)[\'\"]"),
    re.compile(r"process\.env\.(\w+)"),
    re.compile(r"process\.env\[[\'\"](\w+)[\'\"]\]"),
]

CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}


def find_referenced_vars(project_path: Path) -> set[str]:
    found = set()
    for path in project_path.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in CODE_EXTENSIONS:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for pattern in ENV_REF_PATTERNS:
            for m in pattern.finditer(text):
                found.add(m.group(1))
    return found


def parse_env_file(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip()
    return values


def run(project_path: str, interactive: bool) -> None:
    project = Path(project_path).resolve()

    example_vars = set(parse_env_file(project / ".env.example").keys())
    local_vars = parse_env_file(project / ".env")
    code_vars = find_referenced_vars(project)

    required = example_vars | code_vars
    missing = sorted(v for v in required if v not in local_vars)
    unused_locally = sorted(v for v in local_vars if v not in required)

    print(f"Scanned: {project}")
    print(f"Referenced in code: {len(code_vars)} | Declared in .env.example: {len(example_vars)}")
    print()

    if missing:
        print(f"Missing from .env ({len(missing)}):")
        for v in missing:
            print(f"  - {v}")
    else:
        print("Nothing missing — all required vars are set in .env.")

    if unused_locally:
        print()
        print(f"Set in .env but not referenced/declared ({len(unused_locally)}):")
        for v in unused_locally:
            print(f"  - {v}")

    if not missing:
        return

    if not interactive:
        print()
        print("Run with --interactive to fill these in and write .env.")
        return

    print()
    print("Enter values (leave blank to skip):")
    new_lines = []
    if (project / ".env").exists():
        new_lines.append((project / ".env").read_text().rstrip("\n"))
    for var in missing:
        val = input(f"  {var}=")
        if val:
            new_lines.append(f"{var}={val}")
    (project / ".env").write_text("\n".join(l for l in new_lines if l) + "\n")
    print(f"\nUpdated {project / '.env'}")
