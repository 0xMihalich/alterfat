from struct import pack_into

from .base import nodos_asm_5Ah
from .boot import boot_fat16, boot_fat32, fat32_fsinfo
from .dostime import GetDosDateTime
from .error import mkfs_error
from .exfat import exfat
from .fopen import fopen
from .info import fs_info
from .label import *


def calc_size(clusters: int, sector: int, cluster_size: int, fat_copies: int, reserved_size: int, fs: str) -> (int, int):
    
    if fs == 'FAT12':
        factor = 12
        divider = 8
    elif fs == 'FAT16':
        factor = 2
        divider = 1
    elif fs == 'FAT32':
        factor = 4
        divider = 1
    
    fat_size = ((factor * (clusters + 2)) // divider + sector - 1) // sector * sector
    required_size = cluster_size * clusters + fat_copies * fat_size + reserved_size
    
    return fat_size, required_size


def fat(stream: fopen, fs: str, size: int, offset: int=0, volume_label: str='') -> str:
    '''Make FAT12/FAT16/FAT32 File System'''
    
    sector = 512
    sectors = size // sector
    
    signature = 0xAA55

    if sectors < 16 or sectors > 0xFFFFFFFF:
        raise mkfs_error()
    
    if fs == 'exFAT':
        del sector, sectors, signature
        return exfat(stream, size, offset, volume_label)

    if fs == 'FAT12':
        reserved_size = 1 * sector
        root_entries = 224
        
        maxsize_512 = 2097152
        minsize_1024 = 2097152
        maxsize_1024 = 4183040
        minsize_2048 = 4194304
        maxsize_2048 = 8366080
        minsize_4096 = 8388608
        maxsize_4096 = 16732160
        minsize_8192 = 16777216
        maxsize_8192 = 33464320
        minsize_16384 = 33554432
        maxsize_16384 = 66928640
        minsize_32768 = 67108864
        maxsize_32768 = 133857280
        
    elif fs == 'FAT16':
        reserved_size = sector
        root_entries = sector
        
        maxsize_512 = 33554432
        minsize_1024 = maxsize_512
        maxsize_1024 = 67108864
        minsize_2048 = maxsize_1024
        maxsize_2048 = 134217728
        minsize_4096 = maxsize_2048
        maxsize_4096 = 268435456
        minsize_8192 = maxsize_4096
        maxsize_8192 = 536870912
        minsize_16384 = maxsize_8192
        maxsize_16384 = 1073741824
        minsize_32768 = maxsize_16384
        maxsize_32768 = 2147483648
        
    elif fs == 'FAT32':
        reserved_size = 32 * sector
        root_entries = 0
        
        maxsize_512 = 67108864
        minsize_1024 = maxsize_512
        maxsize_1024 = 134217728
        minsize_2048 = maxsize_1024
        maxsize_2048 = 268435456
        minsize_4096 = maxsize_2048
        maxsize_4096 = 8589934592
        minsize_8192 = maxsize_4096
        maxsize_8192 = 17179869184
        minsize_16384 = maxsize_8192
        maxsize_16384 = 34359738368
        minsize_32768 = maxsize_16384
        maxsize_32768 = 2199023255552
    
    fat_copies = 2
    reserved_size += root_entries * 32
    
    allowed = {}

    for i in range(9, 17):
        fsinfo = {}
        cluster_size = (2 ** i)
        clusters = (size - reserved_size) // cluster_size
        fat_size, required_size = calc_size(clusters, sector, cluster_size, fat_copies, reserved_size, fs)
        
        while required_size > size:
            clusters -= 1
            fat_size, required_size = calc_size(clusters, sector, cluster_size, fat_copies, reserved_size, fs)
        
        if fs == 'FAT12':
            if clusters > 4095:
                continue
        elif fs == 'FAT16':
            if 4086 > clusters > 65525:
                continue
        elif fs == 'FAT32':
            if clusters < 65525 or clusters > 0x0FFFFFF6:
                continue
        
        fsinfo['required_size'] = required_size
        fsinfo['reserved_size'] = reserved_size
        fsinfo['cluster_size'] = cluster_size
        fsinfo['clusters'] = clusters
        fsinfo['fat_size'] = fat_size
        fsinfo['root_entries'] = root_entries
        
        allowed[cluster_size] = fsinfo

    if not allowed:
        raise mkfs_error()

    if size <= maxsize_512:
        fsinfo = allowed[512]
    elif minsize_1024 < size <= maxsize_1024:
        fsinfo = allowed[1024]
    elif minsize_2048 < size <= maxsize_2048:
        fsinfo = allowed[2048]
    elif minsize_4096 < size <= maxsize_4096:
        fsinfo = allowed[4096]
    elif minsize_8192 < size <= maxsize_8192:
        fsinfo = allowed[8192]
    elif minsize_16384 < size <= maxsize_16384:
        fsinfo = allowed[16384]
    elif minsize_32768 < size <= maxsize_32768:
        fsinfo = allowed[32768]
    else:
        fsinfo = allowed[65536]

    if fs in ('FAT12', 'FAT16'):
        boot = boot_fat16()
        boot.wMaxRootEntries = fsinfo['root_entries']

        if sectors < 65536:
            boot.wTotalSectors = sectors
        else:
            boot.dwTotalLogicalSectors = sectors

        boot.wSectorsPerFAT = fsinfo['fat_size'] // sector
        boot.uchSignature = 0x29
        
        if fs == 'FAT12':
            boot.wSectorsCount = 1
            boot.dwHiddenSectors = 0
            boot.uchMediaDescriptor = 0xF0
            boot.chPhysDriveNumber = 0
            boot.wSectorsPerTrack = 18
            boot.wHeads = 2
            
            clus_0_2 = b'\xF0\xFF\xFF'

        elif fs == 'FAT16':
            boot.wSectorsCount = (reserved_size - fsinfo['root_entries'] * 32) // sector
            boot.dwHiddenSectors = 1
            boot.uchMediaDescriptor = 0xF8
            boot.chPhysDriveNumber = 0x80
            boot.wSectorsPerTrack = 63
            boot.wHeads = 16
            
            clus_0_2 = b'\xF8\xFF\xFF\xFF'
        
        chOemID = b'NODOS'
        
        root = bytearray(boot.wMaxRootEntries * 32)

    elif fs == 'FAT32':
        boot = boot_fat32()
        boot.wSectorsCount = 6
        boot.wHiddenSectors = 0
        boot.uchMediaDescriptor = 0xF8
        boot.dwTotalLogicalSectors = sectors
        boot.dwSectorsPerFAT = fsinfo['fat_size'] // sector
        boot.dwRootCluster = 2
        boot.wFSISector = 1
        boot.wBootCopySector = 6
        boot.chPhysDriveNumber = 0
        boot.chExtBootSignature = 0x29
        boot.wSectorsPerTrack = 16
        boot.wHeads = 4

        fsi = fat32_fsinfo(offset=sector)
        fsi.sSignature1 = b'RRaA'
        fsi.sSignature2 = b'rrAa'
        fsi.dwFreeClusters = fsinfo['clusters'] - 1
        fsi.dwNextFreeCluster = 3
        fsi.wBootSignature = 0xAA55
        
        clus_0_2 = b'\xF8\xFF\xFF\x0F\xFF\xFF\xFF\xFF\xF8\xFF\xFF\x0F'
        
        chOemID = b'mkdosfs'

    boot.chJumpInstruction = b'\xEB\x58\x90'
    boot._buf[0x5A:0x5A + len(nodos_asm_5Ah)] = nodos_asm_5Ah
    boot.chOemID = b'%-8s' % chOemID
    boot.wBytesPerSector = sector
    boot.uchSectorsPerCluster = fsinfo['cluster_size'] // sector
    boot.uchFATCopies = fat_copies
    boot.dwVolumeID = GetDosDateTime()
    boot.sVolumeLabel = b'%-11s' % b'NO NAME'
    boot.sFSType = b'%-8s' % fs.encode('cp866')
    boot.wBootSignature = signature

    stream.seek(offset)
    stream.write(boot.pack())

    if fs == 'FAT32':
        stream.write(fsi.pack())
        
        root = bytearray(boot.cluster)

    stream.seek(boot.fat() + offset)
    stream.write(bytes(boot.wBytesPerSector * boot.wSectorsPerFAT * 2))

    clus = clus_0_2 + bytes(512 - len(clus_0_2))
    
    stream.seek(boot.wSectorsCount * boot.wBytesPerSector + offset)
    stream.write(clus)

    stream.seek(boot.fat(1) + offset)
    stream.write(clus)

    stream.seek(boot.root() + offset)
    
    if volume_label:
        volume_label = Label(volume_label)
        pack_into('12s', root, 0, VolumeLabel(volume_label))
    
    stream.write(bytes(root))

    stream.flush()

    free_clusters = fsinfo['clusters']

    if fs == 'FAT32':
        free_clusters -= 1

    return fs_info(fs, volume_label, boot.dwVolumeID, free_clusters, boot.cluster, fsinfo)
