from .exfat import exfat
from .fat import fat
from .fopen import fopen
from .handle import handle_list


def fat12(stream: fopen, size: int, offset: int=0, volume_label: str='') -> str:
    return fat(stream, 'FAT12', size, offset, volume_label)


def fat16(stream: fopen, size: int, offset: int=0, volume_label: str='') -> str:
    return fat(stream, 'FAT16', size, offset, volume_label)


def fat32(stream: fopen, size: int, offset: int=0, volume_label: str='') -> str:
    return fat(stream, 'FAT32', size, offset, volume_label)
