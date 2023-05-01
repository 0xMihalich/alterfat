from struct import pack_into


def symbols(name: str, maxlen: int) -> str:
    '''compatible Volume label'''
    
    name = name.rstrip().strip()

    if len(name) > maxlen:
        name = name[:maxlen]

    for symbol in ('*', '?', '/', '\\', '|', ',', ';', ':', '+', '=', '<', '>', '[', ']', '"', '.'):
        if symbol in name:
            name = name.replace(symbol, '_')
    
    return name


def Label(name: str) -> str:
    '''make compatible FAT Volume label'''
    
    return symbols(name, 11)

    
def exLabel(name: str) -> str:
    '''make compatible exFAT Volume label'''
    
    return symbols(name, 15)


def VolumeLabel(label: str) -> bytes:
    '''FAT Volume label'''
    
    count = f'{len(label)}s'
    vol_label = bytearray(bytes(11) + b'\x08')
    pack_into(count, vol_label, 0, label.encode('cp866', 'replace'))
    
    return vol_label
