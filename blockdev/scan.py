from json import loads
from platform import release
from pythoncom import CoInitialize

from wmi import WMI

from .dev import drive_name
from .drive import Drive
from .info import info
from .json_loads import json_loads
from .shell import shell


def scan() -> list:
    '''scan available USB devices'''
    
    devices = {}
    
    try:
        CoInitialize()
        WBEM = WMI()
    
        if not [disk.Name for disk in WBEM.Win32_LogicalDisk(DriveType = 2)]:
            '''Quck check Removable Media'''

            return devices
        
        for drive in WBEM.query('SELECT * FROM Win32_DiskDrive WHERE MediaType = "Removable Media"'):

            if drive.Size:
                devices.update(info(drive, WBEM))
        
        if devices:
            return devices

    except:
        '''continue with PowerShell if any error or devices not found'''

    if release() == '7':
        '''this method don't work with Windows 7'''
        
        return devices
    
    command = "Get-PhysicalDisk | Where-Object CannotPoolReason -Match 'Removable Media' | Select-Object DeviceId, FriendlyName, SerialNumber, Size | ConvertTo-Json"
    
    buf = shell(command)
    
    if buf:
        drives = json_loads(buf)
        command = "Get-Partition | Select-Object DiskNumber, DriveLetter | ConvertTo-Json"
        partitions = json_loads(shell(command))
            
        for drive in drives:
            '''add device and associate with letters'''
            
            id = int(drive['DeviceId'])
            
            letters = []

            for partition in partitions:
                if partition['DiskNumber'] == id:
                    letters.append(partition["DriveLetter"] + ':')
            
            name = drive['FriendlyName']
            serial = drive['SerialNumber']
            path = f'\\\\.\\PHYSICALDRIVE{id}'
            size = drive['Size']
            
            devices.update(drive_name(Drive(name, serial, letters, path, size)))
    
    return devices
