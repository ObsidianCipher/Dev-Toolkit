"""devkit deadcode — flag Python functions/classes that are defined but never referenced."""
import ast
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "dist", "build"}
IGNORE_NAMES = {"__init__", "__main__", "main", "setup"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB — skip anything larger (generated/vendored/binary)


def _iter_py_files(project_path: Path):
    for path in project_path.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        yield path


def _collect_defs_and_uses(files):
    defs = {}  # name -> (file, lineno)
    uses = set()

    for path in files:
        try:
            source = path.read_text(errors="ignore")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, ValueError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    pass  # still track private names, just noted
                defs.setdefault(node.name, (str(path), node.lineno))
            elif isinstance(node, ast.Name):
                uses.add(node.id)
            elif isinstance(node, ast.Attribute):
                uses.add(node.attr)

    return defs, uses


def run(project_path: str) -> None:
    project = Path(project_path).resolve()
    files = list(_iter_py_files(project))

    if not files:
        print(f"No Python files found under {project}")
        return

    defs, uses = _collect_defs_and_uses(files)

    dead = {
        name: loc
        for name, loc in defs.items()
        if name not in uses and name not in IGNORE_NAMES and not name.startswith("test_")
    }

    print(f"Scanned {len(files)} Python file(s) under {project}")
    print()

    if not dead:
        print("No obviously unused top-level functions/classes found.")
        print("(Note: this is a simple name-reference check, not full call-graph analysis —")
        print(" it won't catch dynamic dispatch, decorators-only usage, or re-exports.)")
        return

    print(f"Possibly unused ({len(dead)}):")
    for name, (file, lineno) in sorted(dead.items(), key=lambda kv: kv[1][0]):
        rel = Path(file).relative_to(project) if project in Path(file).parents else file
        print(f"  {rel}:{lineno}  {name}")

    print()
    print("Review before deleting — this is a heuristic, not a guarantee.")
