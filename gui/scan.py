from PyQt5.QtCore import QThread

import blockdev


class Scan(QThread):

    def __init__(self, mainwindow, parent=None):
        super().__init__()
        self.mainwindow = mainwindow

    def run(self):
        ui = self.mainwindow
        
        ui.devices.clear()
        ui.devices.setEnabled(False)
        
        ui.devices.addItem('Scanning...')
        ui.usb_devices = blockdev.scan()
        
        ui.devices.clear()
        ui.devices.addItems(ui.usb_devices)
        ui.devices.setEnabled(True)
