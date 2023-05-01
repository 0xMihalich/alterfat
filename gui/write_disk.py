from PyQt5.QtCore import QThread, pyqtSignal

from mkfs import fat, fopen, handle_list
from mbr import mbr


class WriteDisk(QThread):
    log = pyqtSignal(str)

    def __init__(self, mainwindow, parent=None):
        super().__init__()
        self.mainwindow = mainwindow

    def run(self):
        ui = self.mainwindow
        
        ui.start.setEnabled(False)
        
        drive = ui.devices.currentText()
        usb = ui.usb_devices[drive]
        fs = ui.file_systems.currentText()
        volume_label = ui.volume_label.text()
        
        letters = handle_list(usb.letters)
        path = usb.path
        size = usb.size
        bs = 512
        
        try:
            with fopen(path, "r+b", letters) as stream:
                self.log.emit('Writing MBR...')
                stream.seek(0)
                self.log.emit('')
                stream.write(mbr(size, fs))
                self.log.emit('Write MBR success')
                self.log.emit('')
                self.log.emit(f'Formatting partition to {fs}...')
                self.log.emit('')
                self.log.emit(fat(stream, fs, size - bs, bs, volume_label))
                self.log.emit('')
                self.log.emit('All done. Please, rescan USB devices manually')
        except:
            self.log.emit('')
            self.log.emit('Any error. Please, rescan USB and try again')
