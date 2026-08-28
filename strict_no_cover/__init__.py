from .__main__ import strict_no_cover

__all__ = 'strict_no_cover', '__version__'


def __getattr__(name: str) -> str:
    if name == '__version__':
        from importlib.metadata import version

        return version('strict-no-cover')
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
