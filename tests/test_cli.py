"""End-to-end test of the CLI's report-processing path.

The CLI shells out to `coverage json`. To keep these tests hermetic and
fast, we feed `collect_violation_blocks` a `CoverageReport` mirroring the
real shape that produces a violation, then verify the output formatting
matches what the CLI would print.
"""

from __future__ import annotations

from pathlib import Path

from strict_no_cover.__main__ import (
    CoverageReport,
    FileCoverage,
    collect_violation_blocks,
)


def test_violation_block_formatting(tmp_path: Path) -> None:
    """A single overlapping line produces `'  <path>:N'` with a single-line count."""
    f = tmp_path / 'mymod.py'
    # Line 7 is a plain assignment statement — neither a block opening nor a comment
    f.write_text('x = 1\n' * 6 + 'x = 99\n' * 5)
    report = CoverageReport(
        files={
            str(f): FileCoverage(
                executed_lines=[1, 2, 3, 4, 5, 6, 7],
                excluded_lines=[7],
            ),
        },
    )
    blocks, total = collect_violation_blocks(report)
    assert blocks == [f'  {f}:7']
    assert total == 1


def test_violation_range_formatting(tmp_path: Path) -> None:
    """Adjacent excluded-and-executed lines collapse into a `start to end` range."""
    f = tmp_path / 'mymod.py'
    f.write_text('x = 1\n' * 20)
    report = CoverageReport(
        files={
            str(f): FileCoverage(
                executed_lines=[5, 6, 7],
                excluded_lines=[5, 6, 7],
            ),
        },
    )
    blocks, total = collect_violation_blocks(report)
    assert blocks == [f'  {f}:5 to 7']
    assert total == 3
