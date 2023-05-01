from gui.main import Alterfat


if __name__ == "__main__":
    import sys
    
    from PyQt5.QtWidgets import QApplication


    app = QApplication(sys.argv)
    main = Alterfat()
    main.show()
    sys.exit(app.exec())
