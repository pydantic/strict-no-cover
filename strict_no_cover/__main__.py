from __future__ import annotations

import os
import re
import sys
from importlib.metadata import version as _metadata_version

from coverage import Coverage
from coverage.exceptions import CoverageException


def strict_no_cover() -> int:
    print(f'strict-no-cover v{_metadata_version("strict-no-cover")}')

    exclude_comment = os.getenv('EXCLUDE_COMMENT', 'pragma: no cover')
    coverage_file = os.getenv('COVERAGE_FILE', '.coverage')

    cov = Coverage(data_file=coverage_file)
    cov.config.exclude_list = [exclude_comment]
    try:
        cov.load()
        data = cov.get_data()
    except CoverageException as e:
        print(f'❎ Error loading coverage data: {e}', file=sys.stderr)
        return 1

    blocks: list[str] = []
    total_lines = 0
    for abs_file_name in sorted(data.measured_files()):
        file_name = os.path.relpath(abs_file_name)
        try:
            excluded = cov._analyze(abs_file_name).excluded
        except CoverageException:
            continue

        # Find lines that are both excluded and executed, using raw traced lines since
        # coverage's Analysis.executed strips excluded lines in recent versions
        common_lines = sorted(excluded & set(data.lines(abs_file_name) or ()))

        if not common_lines:
            continue

        code_analyzer = CodeAnalyzer(file_name)

        def add_block(start: int, end: int):
            nonlocal code_analyzer, total_lines

            if not code_analyzer.all_block_openings(start, end):
                b = str(start) if start == end else f'{start} to {end}'
                total_lines += end - start + 1
                blocks.append(f'  {file_name}:{b}')

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

    if blocks:
        print(f"❎ {total_lines} lines wrongly marked with '{exclude_comment}' are covered")
        print('\n'.join(blocks))
        return 1
    else:
        print(f"✅ No lines wrongly marked with '{exclude_comment}'")
        return 0


# python expressions that can open blocks so can have the `# pragma: no cover` comment on them
# even though they're covered
BLOCK_OPENINGS = re.compile(rb'\s*(?:def|async def|@|class|if|elif|else)')


class CodeAnalyzer:
    def __init__(self, file_path: str) -> None:
        with open(file_path, 'rb') as f:
            self.lines: list[bytes] = f.read().splitlines()

    def all_block_openings(self, start: int, end: int) -> bool:
        return all(self._is_block_opening(line_no) for line_no in range(start, end + 1))

    def _is_block_opening(self, line_no: int) -> bool:
        return bool(BLOCK_OPENINGS.match(self.lines[line_no - 1]))


def cli():
    sys.exit(strict_no_cover())


if __name__ == '__main__':
    cli()
