import atexit
import struct
from collections import OrderedDict

from .boot import class2str, common_getattr


class exFATDirentry:
    "Represent an exFAT direntry of one or more slots"

    "Represent a 32 byte exFAT slot"
    # chEntryType bit 7: 0=unused entry, 1=active entry
    volume_label_layout = {
    0x00: ('chEntryType', 'B'), # 0x83, 0x03
    0x01: ('chCount', 'B'), # Label length (max 11 chars)
    0x02: ('sVolumeLabel', '22s'),
    0x18: ('sReserved', '8s') }

    bitmap_layout = {
    0x00: ('chEntryType', 'B'), # 0x81, 0x01
    0x01: ('chFlags', 'B'), # bit 0: 0=1st bitmap, 1=2nd bitmap (T-exFAT only)
    0x02: ('sReserved', '18s'),
    0x14: ('dwStartCluster', '<I'), # typically cluster #2
    0x18: ('u64DataLength', '<Q')	} # bitmap length in bytes

    upcase_layout = {
    0x00: ('chEntryType', 'B'), # 0x82, 0x02
    0x01: ('sReserved1', '3s'),
    0x04: ('dwChecksum', '<I'),
    0x08: ('sReserved2', '12s'),
    0x14: ('dwStartCluster', '<I'),
    0x18: ('u64DataLength', '<Q')	}

    volume_guid_layout = {
    0x00: ('chEntryType', 'B'), # 0xA0, 0x20
    0x01: ('chSecondaryCount', 'B'),
    0x02: ('wChecksum', '<H'),
    0x04: ('wFlags', '<H'),
    0x06: ('sVolumeGUID', '16s'),
    0x16: ('sReserved', '10s') }

    texfat_padding_layout = {
    0x00: ('chEntryType', 'B'), # 0xA1, 0x21
    0x01: ('sReserved', '31s') }

    # A file entry slot group is made of a File Entry slot, a Stream Extension slot and
    # one or more Filename Extension slots
    file_entry_layout = {
    0x00: ('chEntryType', 'B'), # 0x85, 0x05
    0x01: ('chSecondaryCount', 'B'), # other slots in the group (2 minimum, max 18)
    0x02: ('wChecksum', '<H'), # slots group checksum
    0x04: ('wFileAttributes', '<H'), # usual MS-DOS file attributes (0x10 = DIR, etc.)
    0x06: ('sReserved2', '2s'),
    0x08: ('dwCTime', '<I'), # date/time in canonical MS-DOS format
    0x0C: ('dwMTime', '<I'),
    0x10: ('dwATime', '<I'),
    0x14: ('chmsCTime', 'B'), # 10-milliseconds unit (0...199)
    0x15: ('chmsMTime', 'B'),
    0x16: ('chtzCTime', 'B'), # Time Zone in 15' increments (0x80=UTC, ox84=CET, 0xD0=DST)
    0x17: ('chtzMTime', 'B'),
    0x18: ('chtzATime', 'B'),
    0x19: ('sReserved2', '7s') }

    stream_extension_layout = {
    0x00: ('chEntryType', 'B'), # 0xC0, 0x40
    # bit 0: 1=can be allocated
    # bit 1: 1=contiguous contents, FAT is not used
    0x01: ('chSecondaryFlags', 'B'),
    0x02: ('sReserved1', 's'),
    0x03: ('chNameLength', 'B'), # max 255 (but Python 2.7.10 Win32 can't access more than 242!)
    0x04: ('wNameHash', '<H'), # hash of the UTF-16, uppercased filename
    0x06: ('sReserved2', '2s'),
    0x08: ('u64ValidDataLength', '<Q'), # should be real file size
    0x10: ('sReserved3', '4s'),
    0x14: ('dwStartCluster', '<I'),
    0x18: ('u64DataLength', '<Q') } # should be allocated size: in fact, it seems they MUST be equal

    file_name_extension_layout = {
    0x00: ('chEntryType', 'B'), # 0xC1, 0x41
    0x01: ('chSecondaryFlags', 'B'),
    0x02: ('sFileName', '30s') }

    slot_types = {
    0x00: ({0x00: ('sRAW','32s')}, "Unknown"),
    0x01: (bitmap_layout, "Allocation Bitmap"),
    0x02: (upcase_layout, "Upcase Table"),
    0x03: (volume_label_layout, "Volume Label"),
    0x05: (file_entry_layout, "File Entry"),
    0x20: (volume_guid_layout, "Volume GUID"),
    0x21: (texfat_padding_layout, "T-exFAT padding"),
    0x40: (stream_extension_layout, "Stream Extension"),
    0x41: (file_name_extension_layout, "Filename Extension") }

    def __init__ (self, s, pos=-1):
        self._i = 0
        self._buf = s
        self._pos = pos
        self._kv = {}
        self.type = self._buf[0] & 0x7F
        if self.type == 0 or self.type not in self.slot_types:
            pass
        self._kv = self.slot_types[self.type][0].copy() # select right slot type
        self._name = self.slot_types[self.type][1]
        self._vk = {} # { name: offset}
        for k, v in list(self._kv.items()):
            self._vk[v[0]] = k
        if self.type == 5:
            for k in (1,3,4,8,0x14,0x18):
                self._kv[k+32] = self.stream_extension_layout[k]
                self._vk[self.stream_extension_layout[k][0]] = k+32

    __getattr__ = common_getattr

    def __str__ (self):
        return class2str(self, "%s @%x\n" % (self._name, self._pos))

    def pack(self):
        "Update internal buffer"
        for k, v in list(self._kv.items()):
            self._buf[k:k+struct.calcsize(v[1])] = struct.pack(v[1], getattr(self, v[0]))
        if self.type == 5:
            self.wChecksum = self.GetSetChecksum(self._buf) # update the slots set checksum
            self._buf[2:4] = struct.pack('<H', self.wChecksum)
        return self._buf

    @staticmethod
    def DatetimeParse(dwDatetime):
        "Decodes a datetime DWORD into a tuple"
        wDate = (dwDatetime & 0xFFFF0000) >> 16
        wTime = (dwDatetime & 0x0000FFFF)
        return (wDate>>9)+1980, (wDate>>5)&0xF, wDate&0x1F, wTime>>11, (wTime>>5)&0x3F, wTime&0x1F, 0, None

    @staticmethod
    def MakeDosDateTimeEx(t):
        "Encode a tuple into a DOS datetime DWORD"
        cdate = ((t[0]-1980) << 9) | (t[1] << 5) | (t[2])
        ctime = (t[3] << 11) | (t[4] << 5) | (t[5]//2)
        tms = 0
        if t[5] % 2: tms += 100 # odd DOS seconds
        return (cdate<<16 | ctime), tms

    @staticmethod
    def GetDosDateTimeEx():
        "Return a tuple with a DWORD representing DOS encoding of current datetime and 10 milliseconds exFAT tuning"
        tm = datetime.now()
        cdate = ((tm.year-1980) << 9) | (tm.month << 5) | (tm.day)
        ctime = (tm.hour << 11) | (tm.minute << 5) | (tm.second//2)
        tms = tm.microsecond//10000
        if tm.second % 2: tms += 100 # odd DOS seconds
        return (cdate<<16 | ctime), tms

    def IsContig(self, value=0):
        if value:
            self.chSecondaryFlags |= 2
        else:
            return bool(self.chSecondaryFlags & 2)

    def IsDeleted(self):
        return self._buf[0] & 0x80 != 0x80

    def IsDir(self, value=-1):
        "Get or set the slot's Dir DOS permission"
        if value != -1:
            self.wFileAttributes = value
        return (self.wFileAttributes & 0x10) == 0x10

    def IsLabel(self, mark=0):
        "Get or set the slot's Label DOS permission"
        return self.type == 3

    special_lfn_chars = '''"*/:<>?\|''' + ''.join([chr(c) for c in range(32)])

    @staticmethod
    def IsValidDosName(name):
        for c in exFATDirentry.special_lfn_chars:
            if c in name:
                return False
        return True

    def Start(self, cluster=None):
        "Get or set cluster WORDs in slot"
        if cluster != None:
            self.dwStartCluster = cluster
        return self.dwStartCluster

    def Name(self):
        "Decodes the file name"
        ln = ''
        if self.type == 5:
            i = 64
            while i < len(self._buf):
                ln += self._buf[i+2:i+32].decode('utf-16le')
                i += 32
            return ln[:self.chNameLength]
        return ln

    @staticmethod
    def GetNameHash(name):
        "Computate the Stream Extension file name hash (UTF-16 LE encoded)"
        hash = 0
        # 'а' == 'а'.upper() BUT u'а' != u'а'.upper()
        # NOTE: UpCase table SHOULD be used to determine upper cased chars
        # valid in a volume. Windows 10 leaves Unicode surrogate pairs untouched,
        # thus allowing to represent more than 64K chars. Windows 10 Explorer
        # and PowerShell ISE can display such chars, CMD and PowerShell only
        # handle them.
        name = name.decode('utf_16_le').upper().encode('utf_16_le') 
        for c in name:
            hash = (((hash<<15) | (hash >> 1)) & 0xFFFF) + c
            hash &= 0xFFFF
        return hash

    @staticmethod
    def GetSetChecksum(s):
        "Computate the checksum for a set of slots (primary and secondary entries)"
        hash = 0
        for i in range(len(s)):
            if i == 2 or i == 3: continue
            hash = (((hash<<15) | (hash >> 1)) & 0xFFFF) + s[i]
            hash &= 0xFFFF
        return hash

    def GenRawSlotFromName(self, name):
        "Generate the exFAT slots set corresponding to a given file name"
        # File Entry part
        # a Stream Extension and a File Name Extension slot are always present
        self.chSecondaryCount = 1 + (len(name)+14)//15
        self.wFileAttributes = 0x20
        ctime, cms = self.GetDosDateTimeEx()
        self.dwCTime = self.dwMTime = self.dwATime = ctime
        self.chmsCTime = self.chmsMTime = self.chmsATime = cms
        # Stream Extension part
        self.chSecondaryFlags = 1 # base value, to show the entry could be allocated
        name = name.encode('utf_16_le')
        self.chNameLength = len(name)//2
        self.wNameHash = self.GetNameHash(name)

        self.pack()

        # File Name Extension(s) part
        i = len(name)
        k = 0
        while i:
            b = bytearray(32)
            b[0] = 0xC1
            j = min(30, i)
            b[2:2+j] = name[k:k+j]
            i-=j
            k+=j
            self._buf += b

        return self._buf


class FAT:
    "Decodes a FAT (12, 16, 32 o EX) table on disk"
    def __init__ (self, stream, offset, clusters, bitsize=32, exfat=0):
        self.stream = stream
        self.size = clusters # total clusters in the data area (max = 2^x - 11)
        self.bits = bitsize # cluster slot bits (12, 16 or 32)
        self.offset = offset # relative FAT offset (1st copy)
        # CAVE! This accounts the 0-1 unused cluster index?
        self.offset2 = offset + (((clusters*bitsize+7)//8)+511)//512*512 # relative FAT offset (2nd copy)
        self.exfat = exfat # true if exFAT (aka FAT64)
        self.reserved = 0x0FF7
        self.bad = 0x0FF7
        self.last = 0x0FFF
        if bitsize == 32:
            self.fat_slot_size = 4
            self.fat_slot_fmt = '<I'
        else:
            self.fat_slot_size = 2
            self.fat_slot_fmt = '<H'
        if bitsize == 16:
            self.reserved = 0xFFF7
            self.bad = 0xFFF7
            self.last = 0xFFFF
        elif bitsize == 32:
            self.reserved = 0x0FFFFFF7 # FAT32 uses 28 bits only
            self.bad = 0x0FFFFFF7
            self.last = 0x0FFFFFF8
            if exfat: # EXFAT uses all 32 bits...
                self.reserved = 0xFFFFFFF7
                self.bad = 0xFFFFFFF7
                self.last = 0xFFFFFFFF
        # maximum cluster index effectively addressable
        # clusters ranges from 2 to 2+n-1 clusters (zero based), so last valid index is n+1
        self.real_last = min(self.reserved-1, self.size+2-1)
        self.decoded = {} # {cluster index: cluster content}
        self.last_free_alloc = 2 # last free cluster allocated (also set in FAT32 FSInfo)
        self.free_clusters = None # tracks free clusters
        # ordered (by disk offset) dictionary {first_cluster: run_length} mapping free space
        self.free_clusters_map = None
        self.map_free_space()
        self.free_clusters_flag = 1
        
    def __str__ (self):
        return "%d-bit %sFAT table of %d clusters starting @%Xh\n" % (self.bits, ('','ex')[self.exfat], self.size, self.offset)

    def __getitem__ (self, index):
        "Retrieves the value stored in a given cluster index"
        try:
            assert 2 <= index <= self.real_last
        except AssertionError:
            return self.last
        slot = self.decoded.get(index)
        if slot: return slot
        pos = self.offset+(index*self.bits)//8
        self.stream.seek(pos)
        slot = struct.unpack(self.fat_slot_fmt, self.stream.read(self.fat_slot_size))[0]
        #~ print "getitem", self.decoded
        if self.bits == 12:
            # Pick the 12 bits we want
            if index % 2: # odd cluster
                slot = slot >> 4
            else:
                slot = slot & 0x0FFF
        self.decoded[index] = slot
        return slot

    # Defer write on FAT#2 allowing undelete?
    def __setitem__ (self, index, value):
        "Set the value stored in a given cluster index"
        try:
            assert 2 <= index <= self.real_last
        except AssertionError:
            return
            raise FATException("Attempt to set invalid cluster index 0x%X with value 0x%X" % (index, value))
        try:
            assert value <= self.real_last or value >= self.reserved
        except AssertionError:
            return
            raise FATException("Attempt to set invalid cluster index 0x%X with value 0x%X" % (index, value))
        self.decoded[index] = value
        dsp = (index*self.bits)//8
        pos = self.offset+dsp
        if self.bits == 12:
            # Pick and set only the 12 bits we want
            self.stream.seek(pos)
            slot = struct.unpack(self.fat_slot_fmt, self.stream.read(self.fat_slot_size))[0]
            if index % 2: # odd cluster
                # Value's 12 bits moved to top ORed with original bottom 4 bits
                #~ print "odd", hex(value), hex(slot), self.decoded
                value = (value << 4) | (slot & 0xF)
                #~ print hex(value), hex(slot)
            else:
                # Original top 4 bits ORed with value's 12 bits
                #~ print "even", hex(value), hex(slot)
                value = (slot & 0xF000) | value
                #~ print hex(value), hex(slot)
        self.stream.seek(pos)
        value = struct.pack(self.fat_slot_fmt, value)
        self.stream.write(value)
        if self.exfat: return # exFAT has one FAT only (default)
        pos = self.offset2+dsp
        self.stream.seek(pos)
        self.stream.write(value)

    def isvalid(self, index):
        "Tests if index is a valid cluster number in this FAT"
        # Inline explicit test avoiding func call to speed-up
        if (index >= 2 and index <= self.real_last) or self.islast(index) or self.isbad(index):
            return 1
        return 0

    def islast(self, index):
        "Tests if index is the last cluster in the chain"
        return self.last <= index <= self.last+7 # *F8 ... *FF

    def isbad(self, index):
        "Tests if index is a bad cluster"
        return index == self.bad

    def count(self, startcluster):
        "Counts the clusters in a chain. Returns a tuple (<total clusters>, <last cluster>)"
        n = 1
        while not (self.last <= self[startcluster] <= self.last+7): # islast
            startcluster = self[startcluster]
            n += 1
        return (n, startcluster)

    def count_to(self, startcluster, clusters):
        "Finds the index of the n-th cluster in a chain"
        while clusters and not (self.last <= self[startcluster] <= self.last+7): # islast
            startcluster = self[startcluster]
            clusters -= 1
        return startcluster

    def count_run(self, start, count=0):
        """Returns the count of the clusters in a contiguous run from 'start'
        and the next cluster (or END CLUSTER mark), eventually limiting to the first 'count' clusters"""
        #~ print "count_run(%Xh, %d)" % (start, count)
        n = 1
        while 1:
            if self.last <= start <= self.last+7: # if end cluster
                break
            prev = start
            start = self[start]
            # If next LCN is not contig
            if prev != start-1:
                break
            # If max run length reached
            if count > 0:
                if  count-1 == 0:
                    break
                else:
                    count -= 1
            n += 1
        return n, start

    def findmaxrun(self):
        "Finds the greatest cluster run available. Returns a tuple (total_free_clusters, (run_start, clusters))"
        t = 1,0
        maxrun=(0,0)
        n=0
        while 1:
            t = self.findfree(t[0]+1)
            if t[0] < 0: break
            maxrun = max(t, maxrun, key=lambda x:x[1])
            n += t[1]
            t = (t[0]+t[1], t[1])
        return n, maxrun

    def map_free_space(self):
        "Maps the free clusters in an ordered dictionary {start_cluster: run_length}"
        if self.exfat: return
        startpos = self.stream.tell()
        self.free_clusters_map = {}
        FREE_CLUSTERS=0
        if self.bits < 32:
            # FAT16 is max 130K...
            PAGE = self.offset2 - self.offset - (2*self.bits)//8
        else:
            # FAT32 could reach ~1GB!
            PAGE = 1<<20
        END_OF_CLUSTERS = self.offset + (self.size*self.bits+7)//8 + (2*self.bits)//8
        i = self.offset+(2*self.bits)//8 # address of cluster #2
        self.stream.seek(i)
        while i < END_OF_CLUSTERS:
            s = self.stream.read(min(PAGE, END_OF_CLUSTERS-i)) # slurp full FAT, or 1M page if FAT32
            j=0
            while j < len(s):
                first_free = -1
                run_length = -1
                while j < len(s):
                    if self.bits == 32:
                        if s[j] != 0 or s[j+1] != 0 or s[j+2] != 0 or s[j+3] != 0:
                            j += 4
                            if run_length > 0: break
                            continue
                    elif self.bits == 16:
                        if s[j] != 0 or s[j+1] != 0:
                            j += 2
                            if run_length > 0: break
                            continue
                    elif self.bits == 12:
                        # Pick the 12 bits wanted
                        #     0        1        2
                        # AAAAAAAA AAAABBBB BBBBBBBB
                        if not j%3:
                            if s[j] != 0 or s[j+1]>>4 != 0:
                                j += 1
                                if run_length > 0: break
                                continue
                        elif j%3 == 1:
                            j+=1
                            continue # simply skips median byte
                        else: # j%3==2
                            if s[j] != 0 or s[j-1] & 0x0FFF != 0:
                                j += 1
                                if run_length > 0: break
                                continue
                    if first_free < 0:
                        first_free = (i-self.offset+j)*8//self.bits
                        run_length = 0
                    run_length += 1
                    j+=self.bits//8
                if first_free < 0: continue
                FREE_CLUSTERS+=run_length
                self.free_clusters_map[first_free] =  run_length
            i += len(s) # advance to next FAT page to examine
        self.stream.seek(startpos)
        self.free_clusters = FREE_CLUSTERS
        return FREE_CLUSTERS, len(self.free_clusters_map)

    def findfree(self, count=0):
        """Returns index and length of the first free clusters run beginning from
        'start' or (-1,0) in case of failure. If 'count' is given, limit the search
        to that amount."""
        if self.free_clusters_map == None:
            self.map_free_space()
        try:
            i, n = self.free_clusters_map.popitem()
        except KeyError:
            return -1, -1
        if n-count > 0:
            self.free_clusters_map[i+count] = n-count # updates map
        self.free_clusters-=min(n,count)
        return i, min(n, count)
    
    def map_compact(self, strategy=0):
        "Compacts, eventually reordering, the free space runs map"
        if not self.free_clusters_flag: return
        #~ print "Map before:", sorted(self.free_clusters_map.iteritems())
        map_changed = 0
        while 1:
            d=copy.copy(self.free_clusters_map)
            for k,v in sorted(self.free_clusters_map.items()):
                while d.get(k+v): # while contig runs exist, merge
                    v1 = d.get(k+v)
                    d[k] = v+v1
                    del d[k+v]
                    #~ print "Compacted {%d:%d} -> {%d:%d}" %(k,v,k,v+v1)
                    #~ print sorted(d.iteritems())
                    v+=v1
            if self.free_clusters_map != d:
                self.free_clusters_map = d
                map_changed = 1
                continue
            break
        self.free_clusters_flag = 0
        
    # TODO: split very large runs
    # About 12% faster injecting a Python2 tree
    def mark_run(self, start, count, clear=False, offset=0):
        "Marks a range of consecutive FAT clusters (optimized for FAT16/32)"
        if not count: return
        if start<2 or start>self.real_last:
            return
        if self.bits == 12:
            if clear == True:
                self.free_clusters_flag = 1
                self.free_clusters_map[start] = count
            while count:
                self[start] = (start+1, 0)[clear==True]
                start+=1
                count-=1
            return
        dsp = (start*self.bits)//8
        pos = self.offset+dsp
        self.stream.seek(pos + offset)
        if clear:
            for i in range(start, start+count):
                self.decoded[i] = 0
            run = bytearray(count*(self.bits//8))
            self.stream.write(run)
            self.free_clusters_flag = 1
            self.free_clusters_map[start] = count
            if self.exfat: return # exFAT has one FAT only (default)
            # updating FAT2, too!
            self.stream.seek(self.offset2+dsp + offset)
            self.stream.write(run)
            return
        # consecutive values to set
        L = range(start+1, start+1+count)
        for i in L:
            self.decoded[i-1] = i
        self.decoded[start+count-1] = self.last
        # converted in final LE WORD/DWORD array
        L = [struct.pack(self.fat_slot_fmt, x) for x in L]
        L[-1] = struct.pack(self.fat_slot_fmt, self.last)
        run = bytearray().join(L)
        self.stream.write(run)
        if self.exfat: return # exFAT has one FAT only (default)
        # updating FAT2, too!
        pos = self.offset2+dsp
        self.stream.seek(pos + offset)
        self.stream.write(run)

    def alloc(self, runs_map, count, params={}):
        """Allocates a set of free clusters, marking the FAT.
        runs_map is the dictionary of previously allocated runs
        count is the number of clusters to allocate
        params is an optional dictionary of directives to tune the allocation (to be done). 
        Returns the last cluster or raise an exception in case of failure"""
        self.map_compact()

        if self.free_clusters < count:
            raise FATException("FATAL! Free clusters exhausted, couldn't allocate %d, only %d left!" % (count, self.free_clusters))

        last_run = None
        
        while count:
            if runs_map:
                last_run = list(runs_map.items())[-1]
            i, n = self.findfree(count)
            self.mark_run(i, n) # marks the FAT
            if last_run:
                self[last_run[0]+last_run[1]-1] = i # link prev chain with last
            if last_run and i == last_run[0]+last_run[1]: # if contiguous
                runs_map[last_run[0]] = n+last_run[1]
            else:
                runs_map[i] = n
            last = i + n - 1 # last cluster in new run
            count -= n

        self[last] = self.last
        self.last_free_alloc = last

        return last

    def free(self, start, runs=None):
        "Frees a clusters chain, one run at a time (except FAT12)"
        if start < 2 or start > self.real_last:
            return
        self.free_clusters_flag = 1
        if runs:
            for run in runs:
                self.mark_run(run, runs[run], True)
                if not self.exfat:
                    self.free_clusters += runs[run]
                    self.free_clusters_map[run] = runs[run]
            return

        while True:
            length, next = self.count_run(start)
            self.mark_run(start, length, True)
            if not self.exfat:
                self.free_clusters += length
                self.free_clusters_map[start] = length
            start = next
            if self.last <= next <= self.last+7: break


class Chain(object):
    "Opens a cluster chain or run like a plain file"
    def __init__ (self, boot, fat, cluster, size=0, nofat=0, end=0):
        self.isdirectory=False
        self.stream = boot.stream
        self.boot = boot
        self.fat = fat
        self.start = cluster # start cluster or zero if empty
        self.end = end # end cluster
        self.nofat = nofat # 0=uses FAT (fragmented)
        self.size = (size+boot.cluster-1)//boot.cluster*boot.cluster
        # Size in bytes of allocated cluster(s)
        if self.start and (not nofat or not self.fat.exfat):
            if not size or not end:
                self.size, self.end = fat.count(cluster)
                self.size *= boot.cluster
        else:
            self.size = (size+boot.cluster-1)//boot.cluster*boot.cluster
            self.end = cluster + (size+boot.cluster-1)//boot.cluster
        self.filesize = size or self.size # file size, if available, or chain size
        self.pos = 0 # virtual stream linear pos
        # Virtual Cluster Number (cluster index in this chain)
        self.vcn = 0
        # Virtual Cluster Offset (current offset in VCN)
        self.vco = 0
        self.lastvlcn = (0, cluster) # last cluster VCN & LCN
        self.runs = OrderedDict() # RLE map of fragments
        if self.start:
            self._get_frags()

    def __str__ (self):
        return "Chain of %d (%d) bytes from LCN %Xh (LBA %Xh)" % (self.filesize, self.size, self.start, self.boot.cl2offset(self.start))

    def _get_frags(self):
        "Maps the cluster runs composing the chain"
        start = self.start
        if self.nofat:
            self.runs[start] = self.size//self.boot.cluster
        else:
            while 1:
                length, next = self.fat.count_run(start)
                self.runs[start] = length
                if next == self.fat.last or next==start+length-1: break
                start = next

    def _alloc(self, count):
        "Allocates some clusters and updates the runs map. Returns last allocated LCN"
        if self.fat.exfat:
            self.end = self.boot.bitmap.alloc(self.runs, count)
        else:
            self.end = self.fat.alloc(self.runs, count)
        if not self.start:
            self.start = list(self.runs.keys())[0]
        self.nofat = (len(self.runs)==1)
        self.size += count * self.boot.cluster
        return self.end

    def maxrun4len(self, length):
        "Returns the longest run of clusters, up to 'length' bytes, from current position"
        if not self.runs:
            self._get_frags()
        n = (length+self.boot.cluster-1)//self.boot.cluster # contig clusters searched for
        found = 0
        items = list(self.runs.items())
        for start, count in items:
            # if current LCN is in run
            if start <= self.lastvlcn[1] < start+count:
                found=1
                break
        if not found:
            raise FATException("FATAL! maxrun4len did NOT find current LCN!\n%s\n%s" % (self.runs, self.lastvlcn))
        left = start+count-self.lastvlcn[1] # clusters to end of run
        run = min(n, left)
        maxchunk = run*self.boot.cluster
        if n < left:
            next = self.lastvlcn[1]+n
        else:
            i = items.index((start, count))
            if i == len(items)-1:
                next = self.fat.last
            else:
                next = items[i+1][0] # first of next run
        # Updates VCN & next LCN
        self.lastvlcn = (self.lastvlcn[0]+n, next)
        return maxchunk

    def tell(self): return self.pos

    def realtell(self):
        return self.boot.cl2offset(self.lastvlcn[1])+self.vco

    def seek(self, offset, whence=0):
        if whence == 1:
            self.pos += offset
        elif whence == 2:
            if self.size:
                self.pos = self.size + offset
        else:
            self.pos = offset
        # allocate some clusters if needed (in write mode)
        if self.pos > self.size:
            if self.boot.stream.mode == 'r+b':
                clusters = (self.pos+self.boot.cluster-1)//self.boot.cluster - self.size//self.boot.cluster
                self._alloc(clusters)
            else:
                self.pos = self.size
        # Maps Virtual Cluster Number (chain cluster) to Logical Cluster Number (disk cluster)
        self.vcn = self.pos // self.boot.cluster # n-th cluster chain
        self.vco = self.pos % self.boot.cluster # offset in it

        vcn = 0
        for start, count in list(self.runs.items()):
            # if current VCN is in run
            if vcn <= self.vcn < vcn+count:
                lcn = start + self.vcn - vcn
                #~ print "Chain%08X: mapped VCN %d to LCN %Xh (LBA %Xh)"%(self.start, self.vcn, lcn, self.boot.cl2offset(lcn))
                self.stream.seek(self.boot.cl2offset(lcn)+self.vco)
                self.lastvlcn = (self.vcn, lcn)
                #~ print "Set lastvlcn", self.lastvlcn
                return
            vcn += count

    def read(self, size=-1):
        # If negative size, set it to file size
        if size < 0:
            size = self.filesize
        # If requested size is greater than file size, limit to the latter
        if self.pos + size > self.filesize:
            size = self.filesize - self.pos
            if size < 0: size = 0
        buf = bytearray()
        if not size:
            return buf
        self.seek(self.pos) # coerce real stream to the right position!
        if self.nofat: # contiguous clusters
            buf += self.stream.read(size)
            self.pos += size
            return buf
        while 1:
            if not size: break
            n = min(size, self.maxrun4len(size)-self.vco)
            buf += self.stream.read(n)
            size -= n
            self.pos += n
            self.seek(self.pos)
        return buf

    def write(self, s):
        if not s: return
        new_allocated = 0
        if self.pos + len(s) > self.size:
            # Alloc more clusters from actual last one
            # reqb=requested bytes, reqc=requested clusters
            reqb = self.pos + len(s) - self.size
            reqc = (reqb+self.boot.cluster-1)//self.boot.cluster
            self._alloc(reqc)
            new_allocated = 1
        # force lastvlcn update (needed on allocation)
        self.seek(self.pos)
        if self.nofat: # contiguous clusters
            self.stream.write(s)
            self.pos += len(s)
            # file size is the top pos reached during write
            self.filesize = max(self.filesize, self.pos)
            return
        size=len(s) # bytes to do
        i=0 # pos in buffer
        while 1:
            if not size: break
            n = min(size, self.maxrun4len(size)-self.vco) # max bytes to complete run
            self.stream.write(s[i:i+n])
            size-=n
            i+=n
            self.pos += n
            self.seek(self.pos)
        self.filesize = max(self.filesize, self.pos)
        if new_allocated and (not self.fat.exfat or self.isdirectory):
            # When allocating a directory table, it is strictly necessary that only the first byte in
            # an empty slot (the first) is set to NULL
            if self.pos < self.size:
                self.stream.write(bytearray(self.size - self.pos))

    def trunc(self):
        "Truncates the clusters chain to the current one, freeing the rest"
        x = self.pos//self.boot.cluster # last VCN (=actual) to set
        n = (self.size+self.boot.cluster-1)//self.boot.cluster - x - 1 # number of clusters to free
        if not n:
            return 1
        #~ print "%s: truncating @VCN %d, freeing %d clusters. %d %d" % (self, x, n, self.pos, self.size)
        #~ print "Start runs:\n", self.runs
        # Updates chain and virtual stream sizes
        self.size = (x+1)*self.boot.cluster
        self.filesize = self.pos
        while 1:
            if not n: break
            start, length = self.runs.popitem()
            if n >= length:
                #~ print "Zeroing %d from %d" % (length, start)
                if self.fat.exfat:
                    self.boot.bitmap.free1(start, length)
                else:
                    self.fat.mark_run(start, length, True)
                if n == length and (not self.fat.exfat or len(self.runs) > 1):
                    k = list(self.runs.keys())[-1]
                    self.fat[k+self.runs[k]-1] = self.fat.last
                n -= length
            else:
                #~ print "Zeroing %d from %d, last=%d" % (n, start+length-n, start+length-n-1)
                if self.fat.exfat:
                    self.boot.bitmap.free1(start+length-n, n)
                else:
                    self.fat.mark_run(start+length-n, n, True)
                if len(self.runs) or not self.fat.exfat:
                    # Set new last cluster
                    self.fat[start+length-n-1] = self.fat.last
                self.runs[start] = length-n
                n=0
        #~ print "Final runs:\n", self.runs
        #~ for start, length in self.runs.items():
            #~ for i in range(length):
                #~ print "Cluster %d=%d"%(start+i, self.fat[start+i])
        self.nofat = (len(self.runs)==1)
        return 0

    def frags(self):
        return len(self.runs)


class Bitmap(Chain):
    def __init__ (self, boot, fat, cluster, size=0):
        self.isdirectory=False
        self.runs = OrderedDict() # RLE map of fragments
        self.stream = boot.stream
        self.boot = boot
        self.fat = fat
        self.start = cluster # start cluster or zero if empty
        # Size in bytes of allocated cluster(s)
        if self.start:
            self.size = fat.count(cluster)[0]*boot.cluster
        self.filesize = size or self.size # file size, if available, or chain size
        self.pos = 0 # virtual stream linear pos
        # Virtual Cluster Number (cluster index in this chain)
        self.vcn = -1
        # Virtual Cluster Offset (current offset in VCN)
        self.vco = -1
        self.lastvlcn = (0, cluster) # last cluster VCN & LCN
        self.last_free_alloc = 2
        self.nofat = False
        # Bitmap always uses FAT, even if contig, but is fixed size
        self.size == self.maxrun4len(self.size)
        self.free_clusters = None # tracks free clusters number
        self.free_clusters_map = None
        self.free_clusters_flag = 0 # set if map needs compacting
        self.map_free_space()

    def __str__ (self):
        return "exFAT Bitmap of %d bytes (%d clusters) @%Xh" % (self.filesize, self.boot.dwDataRegionLength, self.start)

    def map_free_space(self):
        "Maps the free clusters in an ordered dictionary {start_cluster: run_length}"
        self.free_clusters_map = {}
        FREE_CLUSTERS=0
        # Bitmap could reach 512M!
        PAGE = 1<<20
        END_OF_CLUSTERS = (self.boot.dwDataRegionLength+7)//8
        REMAINDER = 8*END_OF_CLUSTERS - self.boot.dwDataRegionLength
        i = 0 # address of cluster #2
        self.seek(i)
        while i < END_OF_CLUSTERS:
            s = self.read(min(PAGE, END_OF_CLUSTERS-i)) # slurp full bitmap, or 1M page
            j=0
            while j < len(s)*8:
                first_free = -1
                run_length = -1
                while j < len(s)*8:
                    if not j%8 and s[j//8] == 0xFF:
                        if run_length > 0: break
                        j+=8
                        continue
                    if s[j//8] & (1 << (j%8)):
                        if run_length > 0: break
                        j+=1
                        continue
                    if first_free < 0:
                        first_free = j+2+i*8
                        run_length = 0
                    run_length += 1
                    j+=1
                if first_free < 0: continue
                FREE_CLUSTERS+=run_length
                self.free_clusters_map[first_free] =  run_length
            i += len(s) # advance to next Bitmap page to examine
        if REMAINDER:
            FREE_CLUSTERS -= REMAINDER
            last = self.free_clusters_map.popitem()
            run_length = last[1]-REMAINDER # subtracts bits processed in excess
            if run_length > 0:
                self.free_clusters_map[last[0]] =  run_length
        self.free_clusters = FREE_CLUSTERS
        return FREE_CLUSTERS, len(self.free_clusters_map)

    def map_compact(self, strategy=0):
        "Compacts, eventually reordering, the free space runs map"
        if not self.free_clusters_flag: return
        #~ print "Map before:", sorted(self.free_clusters_map.iteritems())
        map_changed = 0
        while 1:
            d=copy.copy(self.free_clusters_map)
            for k,v in sorted(self.free_clusters_map.items()):
                while d.get(k+v): # while contig runs exist, merge
                    v1 = d.get(k+v)
                    d[k] = v+v1
                    del d[k+v]
                    #~ print "Compacted {%d:%d} -> {%d:%d}" %(k,v,k,v+v1)
                    #~ print sorted(d.iteritems())
                    v+=v1
            if self.free_clusters_map != d:
                self.free_clusters_map = d
                map_changed = 1
                continue
            break
        self.free_clusters_flag = 0
        
    def isset(self, cluster):
        "Tests if the bit corresponding to a given cluster is set"
        assert cluster > 1
        cluster-=2
        self.seek(cluster//8)
        B = self.read(1)[0]
        return (B & (1 << (cluster%8))) != 0

    def set(self, cluster, length=1, clear=False):
        "Sets or clears a bit or bits run"
        assert cluster > 1
        cluster-=2 # since bit zero represents cluster #2
        pos = cluster//8
        rem = cluster%8
        self.seek(pos)
        if rem:
            B = self.read(1)[0]
            todo = min(8-rem, length)
            if clear:
                B &= ~((0xFF>>(8-todo)) << rem)
            else:
                B |= ((0xFF>>(8-todo)) << rem)
            self.seek(-1, 1)
            self.write(struct.pack('B',B))
            length -= todo
        octets = length//8
        while octets:
            i = min(32768, octets)
            octets -= i
            if clear:
                self.write(bytearray(i))
            else:
                self.write(i*b'\xFF')
        rem = length%8
        if rem:
            B = self.read(1)[0]
            if clear:
                B &= ~(0xFF>>(8-rem))
            else:
                B |= (0xFF>>(8-rem))
            self.seek(-1, 1)
            self.write(struct.pack('B',B))
    
    def findfree(self, count=0):
        """Returns index and length of the first free clusters run beginning from
        'start' or (-1,-1) in case of failure. If 'count' is given, limit the search
        to that amount."""
        if self.free_clusters_map == None:
            self.map_free_space()
        try:
            i, n = self.free_clusters_map.popitem()
        except KeyError:
            return -1, -1
        if n-count > 0:
            self.free_clusters_map[i+count] = n-count # updates map
        self.free_clusters-=min(n,count)
        return i, min(n, count)

    def findmaxrun(self, count=0):
        "Finds a run of at least count clusters or the greatest run available. Returns a tuple (total_free_clusters, (run_start, clusters))"
        t = self.last_free_alloc,0
        maxrun=(0,0)
        n=0
        while 1:
            t = self.findfree(t[0]+1, count)
            if t[0] < 0: break
            maxrun = max(t, maxrun, key=lambda x:x[1])
            n += t[1]
            if count and maxrun[1] >= count: break # break if we found the required run
            t = (t[0]+t[1], t[1])
        return n, maxrun

    def alloc(self, runs_map, count, params={}):
        """Allocates a set of free clusters, marking the FAT and/or the Bitmap.
        runs_map is the dictionary of previously allocated runs
        count is the number of clusters to allocate
        params is an optional dictionary of directives to tune the allocation (to be done). 
        Returns the last cluster or raise an exception in case of failure"""
        self.map_compact()

        if self.free_clusters < count:
            raise exFATException("FATAL! Free clusters exhausted, couldn't allocate %d, only %d left!" % (count, self.free_clusters))

        last_run = None
        
        while count:
            if runs_map:
                last_run = list(runs_map.items())[-1]
            i, n = self.findfree(count)
            if last_run and i == last_run[0]+last_run[1]: # if contiguous
                runs_map[last_run[0]] = n+last_run[1]
            else:
                runs_map[i] = n
            self.set(i, n) # sets the bitmap
            if len(runs_map) > 1: # if fragmented
                self.fat.mark_run(i, n) # marks the FAT also
                # if just got fragmented...
                if len(runs_map) == 2:
                    if not last_run:
                        last_run = list(runs_map.items())[0]
                    self.fat.mark_run(last_run[0], last_run[1]) # marks the FAT for 1st frag
                self.fat[last_run[0]+last_run[1]-1] = i # linkd prev chain with last
            last = i + n - 1 # last cluster in new run
            count -= n

        if len(runs_map) > 1:
            self.fat[last] = self.fat.last

        self.last_free_alloc = last

        return last

    def free1(self, start, length):
        "Frees the Bitmap only"
        self.free_clusters_flag = 1
        self.free_clusters += length
        self.free_clusters_map[start] = length
        self.set(start, length, True)
        
    def free(self, start, runs=None):
        "Frees the Bitmap following a clusters chain"
        if runs:
            for start, count in list(runs.items()):
                self.free1(start, count)
            return
        while True:
            length, next = self.fat.count_run(start)
            self.free1(start, length) # clears bitmap only, FAT can be dirty
            if next==self.fat.last: break
            start = next
