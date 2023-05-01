from typing import List
import win32file, winioctlcon


def handle(letter: str) -> object:
    '''return PyHANDLE object'''
    
    return win32file.CreateFile('\\\\.\\' + letter, winioctlcon.FILE_READ_DATA | winioctlcon.FILE_WRITE_DATA, win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                                                                                                 None, win32file.OPEN_EXISTING, win32file.FILE_ATTRIBUTE_NORMAL, None)


def handle_list(letters: List[str]) -> List[object]:
    '''return list PyHANDLE objects'''
    
    return [handle(letter) for letter in letters]
