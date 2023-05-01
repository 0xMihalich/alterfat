from struct import pack_into


def mbr(size: int, fs: str='FAT32') -> bytes:
    '''generate mbr block'''
    
    bs = 512
    active = 0 # 128 to active
    size -= bs
    
    if fs in ('FAT12', 'FAT16') and size > 33554432:
        _fs = 6
    else:
        _fs = {'FAT12': 1, 'FAT16': 4, 'FAT32': 11, 'exFAT': 7}[fs]
    
    _mbr = bytearray(bs)
    
    pack_into('<BBBBBBBBII', _mbr, 446, active, 0, 0, 0, _fs, 0, 0, 0, 1, size // bs) # partition config
    pack_into('H', _mbr, 510, 0xaa55) # signature

    return bytes(_mbr)
