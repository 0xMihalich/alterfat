from typing import List

from wmi import _wmi_namespace


def query(DeviceID: str, logical: bool=False) -> str:
    '''construct query for WMI'''
    
    if logical:
        associators = '{Win32_DiskPartition.DeviceID="' + DeviceID + '"}'
        assocclass = 'Win32_LogicalDiskToPartition'
    else:
        associators = '{Win32_DiskDrive.DeviceID="' + DeviceID + '"}'
        assocclass = 'Win32_DiskDriveToDiskPartition'
    
    return f'ASSOCIATORS OF {associators} WHERE AssocClass = {assocclass}'


def letter(DeviceID: str, WBEM: _wmi_namespace) -> List[str]:
    '''get all letters of blockdevice'''
    
    return [logical_disk.DeviceID for partition in WBEM.query(query(DeviceID)) for logical_disk in WBEM.query(query(partition.DeviceID, True))]
    
