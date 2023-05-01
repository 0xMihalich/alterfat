from subprocess import Popen, PIPE


def shell(command: str) -> bytes:
    '''PowerShell output'''

    buffer = Popen(["powershell", "-Command", command], shell=True, stdin=PIPE, stdout=PIPE)
    return buffer.communicate()[0]
