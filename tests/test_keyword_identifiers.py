from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from strict_no_cover import strict_no_cover


@pytest.mark.parametrize(
    'name', ['default_value', 'definition', 'class_name', 'iffy', 'elif_value', 'elsewhere', 'defé']
)
def test_executed_identifier_with_keyword_prefix_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    (tmp_path / 'mod.py').write_text(f'{name} = 1  # pragma: no cover\n', encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'coverage', 'run', 'mod.py'], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)

    assert strict_no_cover() == 1
    assert 'mod.py:1' in capsys.readouterr().out
