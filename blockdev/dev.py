from .drive import Drive
from .convert_size import convert_size


def drive_name(info: Drive) -> dict:
    '''return drive dictionary'''
    
    name = info.name
    serial = info.serial
    letters = ', '.join(info.letters)
    size = convert_size(info.size)
    
    return {f'{name} {serial} ({letters}) [{size}]': info}
