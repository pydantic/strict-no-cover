from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from coverage import CoverageData

from strict_no_cover import strict_no_cover


@pytest.mark.parametrize('data_file', [None, 'custom.coverage', 'missing-directory/custom.coverage'])
def test_absent_coverage_database_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], data_file: str | None
) -> None:
    monkeypatch.chdir(tmp_path)
    if data_file is None:
        monkeypatch.delenv('COVERAGE_FILE', raising=False)
    else:
        monkeypatch.setenv('COVERAGE_FILE', data_file)

    assert strict_no_cover() == 1
    captured = capsys.readouterr()
    assert 'No coverage data file' in captured.err
    assert 'No lines wrongly marked' not in captured.out


@pytest.mark.parametrize('data_file', [None, 'custom.coverage'])
def test_existing_coverage_database_still_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_file: str | None
) -> None:
    monkeypatch.chdir(tmp_path)
    if data_file is None:
        monkeypatch.delenv('COVERAGE_FILE', raising=False)
    else:
        monkeypatch.setenv('COVERAGE_FILE', data_file)
    (tmp_path / 'mod.py').write_text('value = 1\n', encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'coverage', 'run', 'mod.py'], check=True)

    assert strict_no_cover() == 0


def test_existing_empty_coverage_database_still_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('COVERAGE_FILE', raising=False)
    data = CoverageData(basename=str(tmp_path / '.coverage'))
    data.add_lines({str(tmp_path / 'mod.py'): set()})
    data.write()

    assert strict_no_cover() == 0
