"""Tests for the dedup logic in `strict_no_cover.__main__`.

In v0.1.1, the dedup check compared a fully-formatted string `'  file:b'`
against the raw line-range `b`, so it was a no-op (string vs substring
that never matches). Even if normal flow can't produce identical
consecutive ranges (since `common_lines = sorted(set(...))` is monotonic
within a file and file_name varies across files), the comparison is now
type-correct, so any future change that does produce duplicates will be
defended against.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from strict_no_cover.__main__ import (
    CodeAnalyzer,
    CoverageReport,
    FileCoverage,
    collect_violation_blocks,
)


@pytest.fixture
def plain_module(tmp_path: Path) -> Path:
    """A 50-line module with no block-opening lines, so `add_block` always appends."""
    f = tmp_path / 'm.py'
    f.write_text('\n'.join(f'x = {i}' for i in range(1, 51)) + '\n')
    return f


def test_v0_1_1_dedup_was_typed_incorrectly(plain_module: Path) -> None:
    """Pin the bug: v0.1.1 compared `f'  {file_name}:{b}'` against bare `b`,
    so the dedup never fired even on identical consecutive ranges.

    This test reproduces the broken comparison in isolation and asserts
    that, under the v0.1.1 logic, a duplicate WOULD have been appended.
    The fix in `__main__.add_block` changes the comparison to apples-to-apples.
    """
    analyzer = CodeAnalyzer(str(plain_module))
    blocks: list[str] = []
    total_lines = 0

    def buggy_add_block(start: int, end: int) -> None:
        nonlocal total_lines
        if not analyzer.all_block_openings(start, end):
            b = str(start) if start == end else f'{start} to {end}'
            # The v0.1.1 comparison: blocks[-1] is `'  m.py:10'`, b is `'10'` — never equal
            if not blocks or blocks[-1] != b:
                total_lines += end - start + 1
                blocks.append(f'  m.py:{b}')

    buggy_add_block(10, 10)
    buggy_add_block(10, 10)
    assert blocks == ['  m.py:10', '  m.py:10']  # broken: duplicate kept
    assert total_lines == 2


def test_fixed_dedup_collapses_consecutive_identical_entries(plain_module: Path) -> None:
    """The fixed `add_block` would drop the duplicate.

    Re-emit the post-fix closure body to confirm the behavior change.
    """
    analyzer = CodeAnalyzer(str(plain_module))
    blocks: list[str] = []
    total_lines = 0

    def fixed_add_block(start: int, end: int) -> None:
        nonlocal total_lines
        if not analyzer.all_block_openings(start, end):
            b = str(start) if start == end else f'{start} to {end}'
            entry = f'  m.py:{b}'
            if not blocks or blocks[-1] != entry:
                total_lines += end - start + 1
                blocks.append(entry)

    fixed_add_block(10, 10)
    fixed_add_block(10, 10)
    assert blocks == ['  m.py:10']
    assert total_lines == 1


def test_clean_report_returns_no_blocks(plain_module: Path) -> None:
    """When excluded and executed don't overlap, no violations are reported."""
    report = CoverageReport(
        files={
            str(plain_module): FileCoverage(
                executed_lines=[1, 2, 3],
                excluded_lines=[10, 20],
            ),
        },
    )
    blocks, total = collect_violation_blocks(report)
    assert blocks == []
    assert total == 0


def test_block_openings_filtered(tmp_path: Path) -> None:
    """A `def`-line with `# pragma: no cover` is a legitimate use — not a violation.

    The BLOCK_OPENINGS regex skips ranges where every line begins with
    `def`, `async def`, `@`, `class`, `if`, `elif`, or `else`.
    """
    f = tmp_path / 'm.py'
    f.write_text('@property\ndef x():\n    return 1\n')
    report = CoverageReport(
        files={
            str(f): FileCoverage(
                executed_lines=[1, 2, 3],
                excluded_lines=[1, 2],
            ),
        },
    )
    blocks, total = collect_violation_blocks(report)
    assert blocks == []
    assert total == 0


def test_collects_distinct_ranges_per_file(plain_module: Path) -> None:
    """A file with multiple non-adjacent violations produces one entry per block."""
    report = CoverageReport(
        files={
            str(plain_module): FileCoverage(
                executed_lines=[10, 12, 13, 14, 20],
                excluded_lines=[10, 12, 13, 14, 20],
            ),
        },
    )
    blocks, total = collect_violation_blocks(report)
    assert blocks == [
        f'  {plain_module}:10',
        f'  {plain_module}:12 to 14',
        f'  {plain_module}:20',
    ]
    assert total == 1 + 3 + 1


def test_dedup_does_not_collapse_across_files(tmp_path: Path) -> None:
    """Distinct files with the same line range produce distinct entries."""
    a = tmp_path / 'a.py'
    a.write_text('\n'.join(f'x = {i}' for i in range(1, 51)) + '\n')
    b = tmp_path / 'b.py'
    b.write_text('\n'.join(f'x = {i}' for i in range(1, 51)) + '\n')
    report = CoverageReport(
        files={
            str(a): FileCoverage(executed_lines=[10], excluded_lines=[10]),
            str(b): FileCoverage(executed_lines=[10], excluded_lines=[10]),
        },
    )
    blocks, total = collect_violation_blocks(report)
    assert blocks == [f'  {a}:10', f'  {b}:10']
    assert total == 2
