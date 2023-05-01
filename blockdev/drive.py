from typing import NamedTuple, List


class Drive(NamedTuple):
    name: str
    serial: str
    letters: List[str]
    path: str
    size: int
    error: bool = False
