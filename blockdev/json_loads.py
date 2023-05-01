from json import loads
from typing import List


def json_loads(buffer: bytes) -> List[dict]:
    '''List Dictionaries from bytes'''
    
    buffer = loads(buffer)
    
    if isinstance(buffer, dict):
        return [buffer]
    
    return buffer
