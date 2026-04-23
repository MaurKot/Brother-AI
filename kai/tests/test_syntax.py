"""Syntax guard: every python module must compile."""

from pathlib import Path
import py_compile


ROOT = Path(__file__).resolve().parents[1]


def test_all_python_files_compile() -> None:
    failed = []
    for path in ROOT.rglob("*.py"):
        if "state" in path.parts:
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failed.append(f"{path}: {exc.msg}")
    assert not failed, "\n".join(failed)
