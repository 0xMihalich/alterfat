from datetime import datetime
from time import localtime


def GetDosDateTime() -> int:
    "Returns DWORD, representing DOS encoding of current datetime"
    
    tm = localtime()
    cdate = ((tm[0] - 1980) << 9) | (tm[1] << 5) | (tm[2])
    ctime = (tm[3] << 11) | (tm[4] << 5) | (tm[5] // 2)
    
    return cdate << 16 | ctime


def GetDosDateTimeEx() -> int:
    "Return a tuple with a DWORD representing DOS encoding of current datetime and 10 milliseconds exFAT tuning"
    
    tm = datetime.now()
    cdate = ((tm.year - 1980) << 9) | (tm.month << 5) | (tm.day)
    ctime = (tm.hour << 11) | (tm.minute << 5) | (tm.second // 2)
    
    return cdate << 16 | ctime
