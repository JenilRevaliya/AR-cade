import sys
from PyQt5.QtWidgets import QApplication
from ui_homepage import HomePage

def main():
    """
    Main function to launch the AR-cade application.
    """
    app = QApplication(sys.argv)
    home = HomePage()
    home.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()