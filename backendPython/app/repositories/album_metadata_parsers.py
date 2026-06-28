import json
from collections.abc import Sequence
from typing import Any


def parse_genres(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, (bytes, bytearray, str)) or not isinstance(value, Sequence):
        raise ValueError("album genres must be a sequence.")
    return tuple(str(item) for item in value if item)


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
