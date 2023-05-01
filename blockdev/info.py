from wmi import _wmi_object, _wmi_namespace

from .dev import drive_name
from .drive import Drive
from .letter import letter
from .rename import rename
from .size import realsize


def info(drive: _wmi_object, WBEM: _wmi_namespace) -> Drive:
    '''return blockdevice info'''
    
    name = rename(drive.Model)
    serial = drive.SerialNumber
    path = drive.DeviceID
    letters = letter(path, WBEM)
    size, error = realsize(path, drive.Size)
    
    return drive_name(Drive(name, serial, letters, path, size, error))
