from importlib import import_module
from locale import getpreferredencoding
from math import log
from struct import pack, pack_into

from .base import nodos_asm_78h
from .boot import boot_exfat
from .dostime import GetDosDateTimeEx
from .error import mkfs_error
from .exfs import *
from .fopen import fopen
from .info import fs_info
from .label import exLabel


def gen_upcase(internal=0):
    "Generates the full, expanded (128K) UpCase table"
    
    tab = []
    
    pref_enc = getpreferredencoding()
    
    if pref_enc == 'UTF-8':
        pref_enc = 'cp850'
    
    d_tab = import_module('encodings.' + pref_enc).decoding_table
    
    for i in range(256):
        C = d_tab[i].upper().encode('utf_16_le')
        
        if len(bytearray(C)) > 2:
            C = pack('<H', i)
        
        tab += [C]
    
    for i in range(256, 65536):
        try:
            C = chr(i).upper().encode('utf_16_le')
        except UnicodeEncodeError:
            C = pack('<H', i)
        
        if len(bytearray(C)) > 2:
            C = pack('<H', i)
        
        tab += [C]
    
    if internal:
        return tab
    
    return bytearray().join(tab)


def gen_upcase_compressed():
    "Generates a compressed UpCase table"
    
    tab = []
    run = -1
    upcase = gen_upcase(1)
    
    for i in range(65536):
        u = pack('<H',i)
        U = upcase[i]
        
        if u != U:
            rl = i - run
            
            if run > -1 and rl > 2:
                del tab[len(tab) - rl:]
                tab += [b'\xFF\xFF', pack('<H', rl)]
            
            run = -1
        else:
            
            if run < 0:
                run = i
        
        tab += [U]
    
    return bytearray().join(tab)


def calc_cluster(size):
    "Returns a cluster adequate to volume size, MS FORMAT style (exFAT)"
    
    c = 9
    v = 26
    
    for i in range(17):
        
        if size <= 2 ** v:
            return 2 ** c
        c += 1
        v += 1
        if v == 29:
            v += 4
        if v == 39:
            v += 1
    
    return (2 << 25)


def ex_size(clusters: int, sector: int, cluster_size: int, fat_copies: int, reserved_size: int, dataregion_padding: int) -> (int, int):
    
    fat_size = (4 * (clusters + 2) + sector - 1) // sector * sector
    fat_size = (fat_size + cluster_size - 1) // cluster_size * cluster_size
    required_size = cluster_size * clusters + fat_copies * fat_size + reserved_size + dataregion_padding
    
    return fat_size, required_size


def exfat(stream: fopen, size: int, offset: int=0, volume_label: str='') -> str:
    '''Make exFAT File System'''

    sector = 512
    sectors = size // sector

    reserved_size = 65536

    fat_copies = 1

    dataregion_padding = 0

    allowed = {}

    for i in range(9, 25):
        fsinfo = {}
        cluster_size = (2 ** i)
        clusters = (size - reserved_size) // cluster_size
        fat_size, required_size = ex_size(clusters, sector, cluster_size, fat_copies, reserved_size, dataregion_padding)
        
        while required_size > size:
            clusters -= 1
            fat_size, required_size = ex_size(clusters, sector, cluster_size, fat_copies, reserved_size, dataregion_padding)
        
        if clusters < 1 or clusters > 0xFFFFFFFF:
            continue
        
        fsinfo['required_size'] = required_size
        fsinfo['reserved_size'] = reserved_size
        fsinfo['cluster_size'] = cluster_size
        fsinfo['clusters'] = clusters
        fsinfo['fat_size'] = fat_size
        
        allowed[cluster_size] = fsinfo

    if not allowed:
        raise mkfs_error()

    fsinfo = allowed[calc_cluster(size)]

    boot = boot_exfat(offset=offset)
    boot.chJumpInstruction = b'\xEB\x76\x90'
    boot._buf[0x78:0x78 + len(nodos_asm_78h)] = nodos_asm_78h
    boot.chOemID = b'%-8s' % b'EXFAT'
    boot.u64PartOffset = 0x3F
    boot.u64VolumeLength = sectors
    boot.dwFATOffset = (reserved_size + sector - 1) // sector
    boot.dwFATLength = (fsinfo['fat_size'] + sector - 1) // sector
    boot.dwDataRegionOffset = boot.dwFATOffset + boot.dwFATLength + dataregion_padding
    boot.dwDataRegionLength = fsinfo['clusters']
    boot.dwRootCluster = 0
    boot.dwVolumeSerial = GetDosDateTimeEx()
    boot.wFSRevision = 0x100
    boot.wFlags = 0
    boot.uchBytesPerSector = int(log(sector) / log(2))
    boot.uchSectorsPerCluster = int(log(fsinfo['cluster_size'] // sector) / log(2))
    boot.uchFATCopies = fat_copies
    boot.uchDriveSelect = 0x80
    boot.wBootSignature = 0xAA55

    boot.__init2__()

    stream.seek(boot.fatoffs)
    stream.write(bytes(sector * boot.dwFATLength - offset))

    clus_0_2 = b'\xF8\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
    stream.seek(boot.fatoffs)
    stream.write(clus_0_2)

    b = bytearray(32)
    b[0] = 0x81
    bitmap = exFATDirentry(b, 0)
    bitmap.dwStartCluster = 2
    bitmap.u64DataLength = (boot.dwDataRegionLength + 7) // 8

    stream.seek(boot.cl2offset(bitmap.dwStartCluster))
    stream.write(bytes(boot.cluster * ((bitmap.u64DataLength + boot.cluster - 1) // boot.cluster)))

    start = bitmap.dwStartCluster + (bitmap.u64DataLength + boot.cluster - 1) // boot.cluster

    stream.seek(boot.cl2offset(start))
    table = gen_upcase_compressed()
    stream.write(table)

    b = bytearray(32)
    b[0] = 0x82
    upcase = exFATDirentry(b, 0)
    upcase.dwChecksum = boot.GetChecksum(table, True)
    upcase.dwStartCluster = start
    upcase.u64DataLength = len(table)

    boot.dwRootCluster = upcase.dwStartCluster + (upcase.u64DataLength + boot.cluster - 1) // boot.cluster

    empty = bytearray(sector)
    empty[-2] = 0x55
    empty[-1] = 0xAA
    
    vbr = boot.pack() + (empty * 8) + (bytearray(sector) * 2)

    checksum = pack('<I', boot.GetChecksum(vbr))
    checksum = sector // 4 * checksum
    
    stream.seek(offset)
    stream.write((vbr + checksum) * 2)

    stream.seek(boot.root())
    stream.write(bytearray(boot.cluster))

    boot.stream = stream
    fat = FAT(stream, boot.fatoffs, boot.clusters(), bitsize=32, exfat=True)

    fat.mark_run(bitmap.dwStartCluster, (bitmap.u64DataLength + boot.cluster - 1) // boot.cluster)
    fat.mark_run(upcase.dwStartCluster, (upcase.u64DataLength + boot.cluster - 1) // boot.cluster)
    fat[boot.dwRootCluster] = fat.last

    bmp = Bitmap(boot, fat, bitmap.dwStartCluster)
    bmp.set(bitmap.dwStartCluster, (bitmap.u64DataLength + boot.cluster - 1) // boot.cluster)
    bmp.set(upcase.dwStartCluster, (upcase.u64DataLength + boot.cluster - 1) // boot.cluster)
    bmp.set(boot.dwRootCluster)

    boot.bitmap = bmp

    b = bytearray(32)
    if volume_label:
        volume_label = exLabel(volume_label)
        b[0] = 0x83
        b[1] = len(volume_label)
        count = f'{b[1] * 2}s'
        pack_into(count, b, 2, volume_label.encode('utf_16_le'))
    else:
        b[0] = 0x3
    label = exFATDirentry(b, 0)

    stream.seek(boot.root())
    stream.write(label.pack() + bitmap.pack() + upcase.pack())
    
    stream.flush()

    free_clusters = boot.dwDataRegionLength - (bitmap.u64DataLength + boot.cluster - 1) // boot.cluster - (upcase.u64DataLength + boot.cluster - 1) // boot.cluster - 1

    return fs_info('exFAT', volume_label, boot.dwVolumeSerial, free_clusters, boot.cluster, fsinfo)
