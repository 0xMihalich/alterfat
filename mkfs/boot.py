from struct import unpack_from, calcsize, pack


def class2str(c, s):
    "Pretty-prints class contents"
    keys = list(c._kv.keys())
    keys.sort()
    for key in keys:
        o = c._kv[key][0]
        v = getattr(c, o)
        if type(v) in (type(0), type(0)):
            v = hex(v)
        s += '%x: %s = %s\n' % (key, o, v)
    return s


def common_getattr(c, name):
    "Decodes and stores an attribute following special class layout"
    i = c._vk[name]
    fmt = c._kv[i][1]
    cnt = unpack_from(fmt, c._buf, i+c._i) [0]
    setattr(c, name,  cnt)
    return cnt


class boot_fat16(object):
    "FAT12/16 Boot Sector"
    layout = { # { offset: (name, unpack string) }
    0x00: ('chJumpInstruction', '3s'),
    0x03: ('chOemID', '8s'),
    0x0B: ('wBytesPerSector', '<H'),
    0x0D: ('uchSectorsPerCluster', 'B'),
    0x0E: ('wSectorsCount', '<H'),
    0x10: ('uchFATCopies', 'B'),
    0x11: ('wMaxRootEntries', '<H'),
    0x13: ('wTotalSectors', '<H'),
    0x15: ('uchMediaDescriptor', 'B'),
    0x16: ('wSectorsPerFAT', '<H'), #DWORD in FAT32
    0x18: ('wSectorsPerTrack', '<H'),
    0x1A: ('wHeads', '<H'),
    0x1C: ('dwHiddenSectors', '<I'), # Here differs from FAT32
    0x20: ('dwTotalLogicalSectors', '<I'),
    0x24: ('chPhysDriveNumber', 'B'),
    0x25: ('uchCurrentHead', 'B'),
    0x26: ('uchSignature', 'B'), # 0x28 or 0x29
    0x27: ('dwVolumeID', '<I'),
    0x2B: ('sVolumeLabel', '11s'),
    0x36: ('sFSType', '8s'),
    0x1FE: ('wBootSignature', '<H') # 55 AA
    } # Size = 0x200 (512 byte)

    def __init__ (self, s=None, offset=0, stream=None):
        self._i = 0
        self._pos = offset # base offset
        self._buf = s or bytearray(512) # normal boot sector size
        self.stream = stream
        self._kv = self.layout.copy()
        self._vk = {} # { name: offset}
        for k, v in list(self._kv.items()):
            self._vk[v[0]] = k
        self.__init2__()

    def __init2__(self):
        if not self.wBytesPerSector: return
        # Cluster size (bytes)
        self.cluster = self.wBytesPerSector * self.uchSectorsPerCluster
        # Offset of the 1st FAT copy
        self.fatoffs = self.wSectorsCount * self.wBytesPerSector + self._pos
        # Number of clusters represented in this FAT
        # Here the DWORD field seems to be set only if WORD one is too small
        self.fatsize = (self.dwTotalLogicalSectors or self.wTotalSectors)//self.uchSectorsPerCluster
        # Offset of the fixed root directory table (immediately after the FATs)
        self.rootoffs = self.fatoffs + self.uchFATCopies * self.wSectorsPerFAT * self.wBytesPerSector + self._pos
        # Data area offset (=cluster #2)
        self.dataoffs = self.rootoffs + (self.wMaxRootEntries*32)
        # Set for compatibility with FAT32 code
        self.dwRootCluster = 0

    __getattr__ = common_getattr

    def __str__ (self):
        return class2str(self, "FAT12/16 Boot Sector @%x\n" % self._pos)

    def pack(self):
        "Updates internal buffer"
        for k, v in list(self._kv.items()):
            self._buf[k:k+calcsize(v[1])] = pack(v[1], getattr(self, v[0]))
        self.__init2__()
        return self._buf

    def clusters(self):
        "Returns the number of clusters in the data area"
        # Total sectors minus sectors preceding the data area
        return ((self.dwTotalLogicalSectors or self.wTotalSectors) - (self.dataoffs//self.wBytesPerSector)) // self.uchSectorsPerCluster

    def cl2offset(self, cluster):
        "Returns the real offset of a cluster"
        return self.dataoffs + (cluster-2)*self.cluster

    def root(self):
        "Returns the offset of the root directory"
        return self.rootoffs

    def fat(self, fatcopy=0):
        "Returns the offset of a FAT table (the first by default)"
        return self.fatoffs + fatcopy * self.wSectorsPerFAT * self.wBytesPerSector


class boot_fat32(object):
    "FAT32 Boot Sector"
    layout = { # { offset: (name, unpack string) }
    0x00: ('chJumpInstruction', '3s'),
    0x03: ('chOemID', '8s'),
    0x0B: ('wBytesPerSector', '<H'),
    0x0D: ('uchSectorsPerCluster', 'B'),
    0x0E: ('wSectorsCount', '<H'), # reserved sectors (min 32?)
    0x10: ('uchFATCopies', 'B'),
    0x11: ('wMaxRootEntries', '<H'),
    0x13: ('wTotalSectors', '<H'),
    0x15: ('uchMediaDescriptor', 'B'),
    0x16: ('wSectorsPerFAT', '<H'), # not used, see 24h instead
    0x18: ('wSectorsPerTrack', '<H'),
    0x1A: ('wHeads', '<H'),
    0x1C: ('wHiddenSectors', '<H'),
    0x1E: ('wTotalHiddenSectors', '<H'),
    0x20: ('dwTotalLogicalSectors', '<I'),
    0x24: ('dwSectorsPerFAT', '<I'),
    0x28: ('wMirroringFlags', '<H'), # bits 0-3: active FAT, it bit 7 set; else: mirroring as usual
    0x2A: ('wVersion', '<H'),
    0x2C: ('dwRootCluster', '<I'), # usually 2
    0x30: ('wFSISector', '<H'), # usually 1
    0x32: ('wBootCopySector', '<H'), # 0x0000 or 0xFFFF if unused, usually 6
    0x34: ('chReserved', '12s'),
    0x40: ('chPhysDriveNumber', 'B'),
    0x41: ('chFlags', 'B'),
    0x42: ('chExtBootSignature', 'B'),
    0x43: ('dwVolumeID', '<I'),
    0x47: ('sVolumeLabel', '11s'),
    0x52: ('sFSType', '8s'),
    #~ 0x72: ('chBootstrapCode', '390s'),
    0x1FE: ('wBootSignature', '<H') # 55 AA
    } # Size = 0x200 (512 byte)

    def __init__ (self, s=None, offset=0, stream=None):
        self._i = 0
        self._pos = offset # base offset
        self._buf = s or bytearray(512) # normal boot sector size
        self.stream = stream
        self._kv = self.layout.copy()
        self._vk = {} # { name: offset}
        for k, v in list(self._kv.items()):
            self._vk[v[0]] = k
        self.__init2__()

    def __init2__(self):
        if not self.wBytesPerSector: return
        # Cluster size (bytes)
        self.cluster = self.wBytesPerSector * self.uchSectorsPerCluster
        # Offset of the 1st FAT copy
        self.fatoffs = self.wSectorsCount * self.wBytesPerSector + self._pos
        # Data area offset (=cluster #2)
        self.dataoffs = self.fatoffs + self.uchFATCopies * self.dwSectorsPerFAT * self.wBytesPerSector + self._pos
        # Number of clusters represented in this FAT (if valid buffer)
        self.fatsize = self.dwTotalLogicalSectors//self.uchSectorsPerCluster
        if self.stream:
            self.fsinfo = fat32_fsinfo(stream=self.stream, offset=self.wFSISector*self.cluster)
        else:
            self.fsinfo = None

    __getattr__ = common_getattr

    def __str__ (self):
        return class2str(self, "FAT32 Boot Sector @%x\n" % self._pos)

    def pack(self):
        "Updates internal buffer"
        for k, v in list(self._kv.items()):
            self._buf[k:k+calcsize(v[1])] = pack(v[1], getattr(self, v[0]))
        self.__init2__()
        return self._buf

    def clusters(self):
        "Returns the number of clusters in the data area"
        # Total sectors minus sectors preceding the data area
        return (self.dwTotalLogicalSectors - (self.dataoffs//self.wBytesPerSector)) // self.uchSectorsPerCluster

    def cl2offset(self, cluster):
        "Returns the real offset of a cluster"
        return self.dataoffs + (cluster-2)*self.cluster

    def root(self):
        "Returns the offset of the root directory"
        return self.cl2offset(self.dwRootCluster)

    def fat(self, fatcopy=0):
        "Returns the offset of a FAT table (the first by default)"
        return self.fatoffs + fatcopy * self.dwSectorsPerFAT * self.wBytesPerSector


class fat32_fsinfo(object):
    "FAT32 FSInfo Sector (usually sector 1)"
    layout = { # { offset: (name, unpack string) }
    0x00: ('sSignature1', '4s'), # RRaA
    0x1E4: ('sSignature2', '4s'), # rrAa
    0x1E8: ('dwFreeClusters', '<I'), # 0xFFFFFFFF if unused (may be incorrect)
    0x1EC: ('dwNextFreeCluster', '<I'), # hint only (0xFFFFFFFF if unused)
    0x1FE: ('wBootSignature', '<H') # 55 AA
    } # Size = 0x200 (512 byte)

    def __init__ (self, s=None, offset=0, stream=None):
        self._i = 0
        self._pos = offset # base offset
        self._buf = s or bytearray(512) # normal FSInfo sector size
        self.stream = stream
        self._kv = self.layout.copy()
        self._vk = {} # { name: offset}
        for k, v in list(self._kv.items()):
            self._vk[v[0]] = k

    __getattr__ = common_getattr

    def pack(self):
        "Updates internal buffer"
        for k, v in list(self._kv.items()):
            self._buf[k:k+calcsize(v[1])] = pack(v[1], getattr(self, v[0]))
        return self._buf

    def __str__ (self):
        return class2str(self, "FAT32 FSInfo Sector @%x\n" % self._pos)


class boot_exfat(object):
    "exFAT boot sector"
    layout = { # { offset: (nome, stringa di unpack) }
    0x00: ('chJumpInstruction', '3s'),
    0x03: ('chOemID', '8s'),
    0x0B: ('chDummy', '53s'),
    0x40: ('u64PartOffset', '<Q'),
    0x48: ('u64VolumeLength', '<Q'), # sectors
    0x50: ('dwFATOffset', '<I'), # sectors
    0x54: ('dwFATLength', '<I'), # sectors
    0x58: ('dwDataRegionOffset', '<I'), # sectors
    0x5C: ('dwDataRegionLength', '<I'), # clusters
    0x60: ('dwRootCluster', '<I'), # cluster index
    0x64: ('dwVolumeSerial', '<I'),
    0x68: ('wFSRevision', '<H'), # 0x100 or 1.00
    # bit 0: active FAT & Bitmap (0=first, 1=second)
    # bit 1: volume is dirty? (0=clean)
    # bit 2: media failure (0=none, 1=some I/O failed)
    0x6A: ('wFlags', '<H'), # field not included in VBR checksum
    0x6C: ('uchBytesPerSector', 'B'), # 2 exponent
    0x6D: ('uchSectorsPerCluster', 'B'), # 2 exponent
    0x6E: ('uchFATCopies', 'B'), # 1 by default
    0x6F: ('uchDriveSelect', 'B'),
    0x70: ('uchPercentInUse', 'B'), # field not included in VBR checksum
    0x71: ('chReserved', '7s'),
    0x1FE: ('wBootSignature', '<H') } # Size = 0x200 (512 byte)

    def __init__ (self, s=None, offset=0, stream=None):
        self._i = 0
        self._pos = offset # base offset
        self._buf = s or bytearray(512) # normal boot sector size
        self.stream = stream
        self._kv = self.layout.copy()
        self._vk = {} # { name: offset}
        for k, v in list(self._kv.items()):
            self._vk[v[0]] = k
        self.__init2__()

    def __init2__(self):
        if not self.uchBytesPerSector: return
        # Cluster size (bytes)
        self.cluster = (1 << self.uchBytesPerSector) * (1 << self.uchSectorsPerCluster)
        # FAT offset
        self.fatoffs = self.dwFATOffset * (1 << self.uchBytesPerSector) + self._pos
        # Clusters in the Data region
        self.fatsize = self.dwDataRegionLength
        # Data region offset (=cluster #2)
        self.dataoffs = self.dwDataRegionOffset * (1 << self.uchBytesPerSector) + self._pos

    __getattr__ = common_getattr

    def pack(self):
        "Updates internal buffer"
        for k, v in list(self._kv.items()):
            self._buf[k:k+calcsize(v[1])] = pack(v[1], getattr(self, v[0]))
        self.__init2__()
        return self._buf

    def __str__ (self):
        return class2str(self, "exFAT Boot sector @%x\n" % self._pos)

    def clusters(self):
        "Returns the number of clusters in the data area"
        # Total sectors minus sectors preceding the data area
        return self.fatsize

    def cl2offset(self, cluster):
        "Returns a real cluster offset"
        return self.dataoffs + (cluster-2)*self.cluster

    def root(self):
        "Root offset"
        return self.cl2offset(self.dwRootCluster)

    @staticmethod
    def GetChecksum(s, UpCase=False):
        "Computates the checksum for the VBR sectors (the first 11) or the UpCase table"
        hash = 0
        for i in range(len(s)):
            if not UpCase and i in (106, 107, 112): continue
            hash = (((hash<<31) | (hash >> 1)) & 0xFFFFFFFF) + s[i] # 10.3.19: when called from test_inject (VBR read into) it is a *string* buffer instead of bytearray: investigate!
            hash &= 0xFFFFFFFF
        return hash
