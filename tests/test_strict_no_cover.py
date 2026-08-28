from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from strict_no_cover import strict_no_cover

COVERED_BODY_LINE = """\
def foo(x):
    if x:  # pragma: no cover
        y = 1
        return y
    return 0


foo(1)
foo(0)
"""

EXECUTED_SIGNATURE_STUB = """\
def stub(
    x: int,
    y: str,
) -> None: ...  # pragma: no cover


def real():
    return 1


real()
"""


def run_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str) -> int:
    (tmp_path / 'mod.py').write_text(source)
    subprocess.run([sys.executable, '-m', 'coverage', 'run', 'mod.py'], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    return strict_no_cover()


def test_covered_body_line_is_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_check(tmp_path, monkeypatch, COVERED_BODY_LINE) == 1
    out = capsys.readouterr().out
    assert 'mod.py:2 to 4' in out


def test_executed_signature_stub_is_not_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert run_check(tmp_path, monkeypatch, EXECUTED_SIGNATURE_STUB) == 0
    out = capsys.readouterr().out
    assert 'No lines wrongly marked' in out
