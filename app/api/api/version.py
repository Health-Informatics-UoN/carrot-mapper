from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("api")
except PackageNotFoundError:
    __version__ = "unknown"
