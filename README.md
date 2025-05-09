# strict-no-cover

Error on unnecessary `pragma: no cover`s comments.

Utility to report `# pragma: no cover` comments which are unnecessary (where some of the relevant lines are actually covered).

## Install

```bash
uv add --dev strict-no-cover
```

## Usage

Run with

```bash
uv run strict-no-cover
```

For cases with flakey coverage or partial coverage on code, use `# pragma: lax no cover` which will not error if some relevant lines are covered.

You'll want to modify `pyproject.toml` to include the following:

```toml
[tool.coverage.report]
exclude_lines = [
    # `# pragma: no cover` is standard marker for code that's not covered, this will error if code is covered
    'pragma: no cover',
    # use `# pragma: lax no cover` if you want to ignore cases where (some of) the code is covered
    'pragma: lax no cover',
    'raise NotImplementedError',
    ...
]
```
