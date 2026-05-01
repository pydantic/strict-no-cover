from __future__ import annotations

import os
import re
import subprocess
import sys
from importlib.metadata import version as _metadata_version
from tempfile import NamedTemporaryFile

from pydantic import BaseModel


def strict_no_cover() -> int:
    print(f'strict-no-cover v{_metadata_version("strict-no-cover")}')

    exclude_comment = os.getenv('EXCLUDE_COMMENT', 'pragma: no cover')
    coverage_file = os.getenv('COVERAGE_FILE', '.coverage')

    with NamedTemporaryFile(suffix='.json') as coverage_json:
        with NamedTemporaryFile(mode='w', suffix='.toml') as config_file:
            config_file.write(f"[tool.coverage.report]\nexclude_lines = ['{exclude_comment}']\n")
            config_file.flush()
            p = subprocess.run(
                ['uv', 'run', 'coverage', 'json', f'--rcfile={config_file.name}', '-o', coverage_json.name, "--data-file", coverage_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if p.returncode != 0:
                print(f'❎ Error running `coverage json`:\n{p.stdout.decode().rstrip()}', file=sys.stderr)
                return p.returncode

        report = CoverageReport.model_validate_json(coverage_json.read())

    blocks, total_lines = collect_violation_blocks(report)

    if blocks:
        print(f"❎ {total_lines} lines wrongly marked with '{exclude_comment}' are covered")
        print('\n'.join(blocks))
        return 1
    else:
        print(f"✅ No lines wrongly marked with '{exclude_comment}'")
        return 0


def collect_violation_blocks(report: CoverageReport) -> tuple[list[str], int]:
    """Return (formatted block lines, total covered-line count) for violations.

    Pure function over an already-parsed `CoverageReport`. Extracted from
    `strict_no_cover()` so the block-merging + dedup logic is unit-testable
    without going through the `coverage json` subprocess.
    """
    blocks: list[str] = []
    total_lines = 0
    for file_name, file_coverage in report.files.items():
        # Find lines that are both excluded and executed
        common_lines = sorted(set(file_coverage.excluded_lines) & set(file_coverage.executed_lines))

        if not common_lines:
            continue

        code_analyzer = CodeAnalyzer(file_name)

        def add_block(start: int, end: int) -> None:
            nonlocal total_lines

            if not code_analyzer.all_block_openings(start, end):
                b = str(start) if start == end else f'{start} to {end}'
                # Dedup consecutive identical entries — compare full formatted strings
                # so the check is type-correct (the bug in v0.1.1 compared 'file:b' against 'b').
                entry = f'  {file_name}:{b}'
                if not blocks or blocks[-1] != entry:
                    total_lines += end - start + 1
                    blocks.append(entry)

        first_line, *rest = common_lines
        current_start = current_end = first_line

        for line in rest:
            if line == current_end + 1:
                current_end = line
            else:
                # Start a new block
                add_block(current_start, current_end)
                current_start = current_end = line

        add_block(current_start, current_end)

    return blocks, total_lines


class FileCoverage(BaseModel):
    executed_lines: list[int]
    excluded_lines: list[int]


class CoverageReport(BaseModel):
    files: dict[str, FileCoverage]


# python expressions that can open blocks so can have the `# pragma: no cover` comment on them
# even though they're covered
BLOCK_OPENINGS = re.compile(rb'\s*(?:def|async def|@|class|if|elif|else)')


class CodeAnalyzer:
    def __init__(self, file_path: str) -> None:
        with open(file_path, 'rb') as f:
            content = f.read()
        self.lines: dict[int, bytes] = dict(enumerate(content.splitlines(), start=1))

    def all_block_openings(self, start: int, end: int) -> bool:
        return all(self._is_block_opening(line_no) for line_no in range(start, end + 1))

    def _is_block_opening(self, line_no: int) -> bool:
        return bool(BLOCK_OPENINGS.match(self.lines[line_no]))


def cli():
    sys.exit(strict_no_cover())


if __name__ == '__main__':
    cli()
