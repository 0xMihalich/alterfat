from typing import List


def access_fs(size: int) -> List[str]:
    '''return list of available FATFS'''
    
    access = []
    
    _fs = {
           'FAT12': (9216, 268435456),
           'FAT16': (8388608, 4294901760),
           'FAT32': (34089472, 2199023255040),
           'exFAT': (7340032, 2199023255040)
          }
    
    for fat, min_max in _fs.items():
        if min_max[0] <= size <= min_max[1]:
            access.append(fat)
    
    return access
