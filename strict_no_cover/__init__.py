from importlib.metadata import version as _metadata_version

from .__main__ import strict_no_cover

__version__ = _metadata_version('strict-no-cover')

__all__ = 'strict_no_cover', '__version__'
