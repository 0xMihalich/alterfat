from struct import calcsize, unpack
from win32file import CreateFile, DeviceIoControl, GENERIC_READ, OPEN_EXISTING
from winioctlcon import IOCTL_DISK_GET_LENGTH_INFO
from pywintypes import error


def realsize(DeviceID: str, Size: str) -> int:
    '''realsize of blockdevice'''
    
    try:
        handle = CreateFile(DeviceID, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
        return unpack('Q', DeviceIoControl(handle, IOCTL_DISK_GET_LENGTH_INFO, None, calcsize('LL'), None))[0], False
    except error:
        return int(Size), True
