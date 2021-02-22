from PySide2 import QtWidgets, QtCore

import platform
import os

from retcom import *

def tessExists() -> bool:
    res = False
    pltfm = platform.system()

    if pltfm == 'Windows':
        res = commandExistsNT('tesseract')
    elif pltfm in ['Darwin', 'Linux']:
        res = commandExistsPOSIX('tesseract')

    return res

def commandExistsPOSIX(cmd:str) -> bool:
    res = os.system(f'command -v {cmd}')

    return (str(res) == '0')

def commandExistsNT(cmd:str) -> bool:
    res = os.system(f'where {cmd}')

    return (str(res) == '0')

class CheckTess(QtWidgets.QMainWindow):
    def __init__(self, retcomconfig, translator, parent=None):
        super(CheckTess, self).__init__(parent=parent)

        self.retcomconfig = retcomconfig
        self.translator = translator

        self.parent = parent

        self.setWindowTitle(f'RetCom | OCR Compatibility')
        self.setGeometry(300, 200, 640, 520)

        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        self.instructionText = QtWidgets.QLabel(self)

        self.okButton = QtWidgets.QPushButton('OK')


        self.layout = QtWidgets.QVBoxLayout()
        self.gridLayout = QtWidgets.QGridLayout()

        self.widget.setLayout(self.layout)
        self.layout.addWidget(self.instructionText, 0, QtCore.Qt.AlignLeft)

        self.gridLayout.addWidget(self.okButton, 0, 0)
        self.layout.addLayout(self.gridLayout)

        self.layout.addStretch()

        self.okButton.clicked.connect(self.onOK)
        self.okButton.setDefault(True)
        self.okButton.setAutoDefault(True)

        self.createUI()

        self.adjustSize()

    def createUI(self):
        pltfm = platform.system()
        if pltfm == 'Windows':
            self.instructionText.setText('Install tesseract-ocr from <a href="https://digi.bib.uni-mannheim.de/tesseract/">here</a> to use OCR.')
        elif pltfm == 'Darwin':
            self.instructionText.setText('Install tesseract-ocr using Brew or MacPorts to use OCR.')
        elif pltfm == 'Linux':
            self.instructionText.setText('Install tesseract-ocr using <a href="https://tesseract-ocr.github.io/tessdoc/Installation.html">these instructions</a> to use OCR.')
        else:
            self.instructionText.setText('OCR will probably not work on this platform.')

    @QtCore.Slot()
    def onOK(self):
        self.close()
        RetCom.openRetCom(self.retcomconfig, self.translator)


if __name__=="__main__":
    print(commandExistsPOSIX('tesssdract'))
    print(commandExistsPOSIX('tesseract'))

# tesseract-ocr-w32-setup-v4.1.0.20190314.exe