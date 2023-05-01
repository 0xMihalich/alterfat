from PyQt5.QtCore import QSize, QRect, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, QPushButton, QComboBox, QLabel, QLineEdit, QTextBrowser

from access import access_fs
from .logo import LOGO
from .scan import Scan
from .write_disk import WriteDisk


class Alterfat(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        
        self.setMinimumSize(QSize(420, 440))
        self.setWindowTitle("AlterFAT")
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

        self.icon = QPixmap()
        self.icon.loadFromData(LOGO)
        self.setWindowIcon(QIcon(self.icon))
        
        self.usb_devices = {}
        self.fs = []
        
        self.scanUSB = Scan(mainwindow=self)
        self.formatUSB = WriteDisk(mainwindow=self)
        self.formatUSB.log.connect(self.logging)
        
        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        
        self.widget = QWidget(self.centralwidget)
        self.widget.setGeometry(QRect(10, 10, 400, 420))
        self.widget.setObjectName("widget")
        
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        
        self.scan = QPushButton(self.widget)
        self.scan.setObjectName("scan")
        self.scan.setText("Scan USB")
        self.scan.clicked.connect(self.scan_usb)
        self.gridLayout.addWidget(self.scan, 0, 0, 1, 1)
        
        self.devices = QComboBox(self.widget)
        self.devices.setObjectName("devices")
        self.devices.currentIndexChanged.connect(self.select_fat)
        self.gridLayout.addWidget(self.devices, 0, 1, 1, 1)
        
        self.file_system = QLabel(self.widget)
        self.file_system.setAlignment(Qt.AlignCenter)
        self.file_system.setObjectName("file_system")
        self.file_system.setText("File System:")
        self.gridLayout.addWidget(self.file_system, 1, 0, 1, 1)
        
        self.file_systems = QComboBox(self.widget)
        self.file_systems.setObjectName("file_systems")
        self.gridLayout.addWidget(self.file_systems, 1, 1, 1, 1)
        
        self.volume = QLabel(self.widget)
        self.volume.setAlignment(Qt.AlignCenter)
        self.volume.setObjectName("volume")
        self.volume.setText("Volume Label:")
        self.gridLayout.addWidget(self.volume, 2, 0, 1, 1)
        
        self.volume_label = QLineEdit(self.widget)
        self.volume_label.setObjectName("volume_label")
        self.gridLayout.addWidget(self.volume_label, 2, 1, 1, 1)
        
        self.log = QTextBrowser(self.widget)
        self.log.setObjectName("log")
        self.gridLayout.addWidget(self.log, 3, 0, 1, 2)
        
        self.start = QPushButton(self.widget)
        self.start.setObjectName("start")
        self.start.setText("Quick Format")
        self.start.setEnabled(False)
        self.start.clicked.connect(self.format)
        self.gridLayout.addWidget(self.start, 4, 0, 1, 2)
        
        self.setCentralWidget(self.centralwidget)
        self.scanUSB.start()

    def logging(self, text):
        self.log.append(text)

    def scan_usb(self):
        self.scanUSB.start()

    def select_fat(self):
        self.file_systems.clear()
        drive = self.devices.currentText()
        if drive and drive != 'Scanning...':
            usb = self.usb_devices[drive]
            self.file_systems.addItems(access_fs(usb.size))
            if usb.error:
                self.log.setText('Failed to get write access. Disk allready used by another program')
                self.start.setEnabled(False)
            else:
                self.log.clear()
                self.start.setEnabled(True)

    def format(self):
        self.formatUSB.start()
