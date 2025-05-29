from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class FileHandlerConfig:
    handler: Callable[[], Any]
    file_type_value: str
    file_extension: str
