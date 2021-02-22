import sys
import os
import subprocess
import json
from collections import defaultdict
import difflib
import uuid

# import fs
# import fs.copy
# import fs.zipfs
import zipfile
import rarfile

from PySide2 import QtCore, QtWidgets, QtGui

from parse_lstmbox import LSTMBox
from fontspecs import FontGeom, full2halfWidth, half2fullWidth
from translator import Translator
from imagetools import *

from PIL import Image, ImageDraw, ImageQt
import cv2

# Change cwd
os.chdir(os.path.dirname(sys.argv[0]))
CWD = os.getcwd()

class RetComConfig(object):
    """RetCom configuration settings.

    This class is mostly limited to internal use, and is intended to be
    initialized by reading a JSON file.

    Args:
        path (str): Config file path.

    Attributes:
        path (str): Config file path.
        json (dict): JSON dictionary. When JSON file does not exist or
            is faulty, an empty dictionary is created instead.
        language (str): Tesseract language code. Multiple languages may
            be assigned by concatenating them with a `+`. Defaults to
            `jpn_vert`.
        isVertical (bool): Flag whether text is vertical or not.
            Defaults to `True`.
        doPrescan (bool): If true, prescans of the image are done in
            advance by default. Defaults to `True`.
        fullWidth (bool): If true, half-width characters are
            automatically treated as full-width CJK characters. Defaults
            to `True`.
        changeCheckThreshold (int): File size threshold for change
            checking. If the file size exceeds the threshold, no checks
            are performed, and a warning dialog is always shown on exit.
            Defaults to 7 KB.
        fontPath (str): Relative font path location. Defaults to
            `fonts`.
        font (str): Default font name used in font size detection.
            Defaults to `GenEiAntiquePv5-M.ttf`.
        boxPath (str): Relative box path location. Defaults to `box`.
    """

    def __init__(self, path:str='./config/config.json'):
        self.path = path

        try:
            with open(path, encoding="utf8") as f:
                self.json = json.load(f)
        except OSError:
            self.json = {}

        self.language = self.json.get('language') if self.json.get('language') else 'jpn_vert'
        self.translationLanguage = self.json.get('translationLanguage') if self.json.get('translationLanguage') else 'en'
        self.isVertical = self.json.get('isVertical') if (self.json.get('isVertical') is not None) else True
        self.doPrescan = self.json.get('doPrescan') if (self.json.get('doPrescan') is not None) else True
        self.fullWidth = self.json.get('fullWidth') if (self.json.get('fullWidth') is not None) else True

        self.changeCheckThreshold = int(self.json.get('changeCheckThreshold')) if self.json.get('changeCheckThreshold') else int(7e3)

        self.fontPath = self.json.get('fontPath') if self.json.get('fontPath') else 'fonts'
        self.font = self.json.get('font') if self.json.get('font') else 'GenEiAntiquePv5-M.ttf'
        self.boxPath = self.json.get('boxPath') if self.json.get('boxPath') else 'box'

        self.suspiciousAspectRatio = self.json.get('suspiciousAspectRatio') if self.json.get('suspiciousAspectRatio') else 2
        self.scaleMultiplier = self.json.get('scaleMultiplier') if self.json.get('scaleMultiplier') else 0.1
        self.fineScaleMultiplier = self.json.get('fineScaleMultiplier') if self.json.get('fineScaleMultiplier') else 0.05

        self.nudgeAmount = self.json.get('nudgeAmount') if self.json.get('nudgeAmount') else 5
        self.fineNudgeAmount = self.json.get('fineNudgeAmount') if self.json.get('fineNudgeAmount') else 1

        self.collationString = self.json.get('collationString') if self.json.get('collationString') else ''

        self.boundingBoxOpacity = self.json.get('boundingBoxOpacity') if self.json.get('boundingBoxOpacity') else 0.5
        self.groupBoxOpacity = self.json.get('groupBoxOpacity') if self.json.get('groupBoxOpacity') else 0.35

        self.boundingBoxColor = QtGui.QColor(self.hex2int(self.json.get('colors').get('boundingBox'))) if self.json.get('colors').get('boundingBox') else 0xFF0000
        self.boundingBoxPattern = eval(f"QtCore.Qt.{self.json.get('boundingBoxPattern')}Pattern") if self.json.get('boundingBoxPattern') else QtCore.Qt.SolidPattern
        self.boundingBoxBrush = QtGui.QBrush(self.boundingBoxColor)
        self.boundingBoxBrush.setStyle(self.boundingBoxPattern)

        self.groupBoxColor    = QtGui.QColor(self.hex2int(self.json.get('colors').get('groupBox')))    if self.json.get('colors').get('groupBox')    else 0xC0C0C0
        self.groupBoxPattern  = eval(f"QtCore.Qt.{self.json.get('groupBoxPattern')}Pattern") if self.json.get('groupBoxPattern') else QtCore.Qt.BDiagPattern
        self.groupBoxBrush    = QtGui.QBrush(self.groupBoxColor)
        self.groupBoxBrush.setStyle(self.groupBoxPattern)

        self.groupBoxStrokeWidth = self.json.get('groupBoxStrokeWidth') if self.json.get('groupBoxStrokeWidth') else 5
        self.groupBoxPen = QtGui.QPen(self.groupBoxColor)
        self.groupBoxPen.setWidth(self.groupBoxStrokeWidth)

        self.fillerBoxColor   = QtGui.QColor(self.hex2int(self.json.get('colors').get('fillerBox')))   if self.json.get('colors').get('fillerBox')   else 0x008000
        self.textBoxColor     = QtGui.QColor(self.hex2int(self.json.get('colors').get('textBox')))   if self.json.get('colors').get('textBox')   else 0xF0E442
        self.flaggedBoxColor  = QtGui.QColor(self.hex2int(self.json.get('colors').get('flaggedBox')))  if self.json.get('colors').get('flaggedBox')  else 0xFF00FF
        self.selectedBoxColor = QtGui.QColor(self.hex2int(self.json.get('colors').get('selectedBox'))) if self.json.get('colors').get('selectedBox') else 0x0000FF

        self.fillerBoxBrush = QtGui.QBrush(self.fillerBoxColor)
        self.fillerBoxBrush.setStyle(self.boundingBoxPattern)
        self.textBoxBrush = QtGui.QBrush(self.textBoxColor)
        self.textBoxBrush.setStyle(self.boundingBoxPattern)
        self.flaggedBoxBrush = QtGui.QBrush(self.flaggedBoxColor)
        self.flaggedBoxBrush.setStyle(self.boundingBoxPattern)
        self.selectedBoxBrush = QtGui.QBrush(self.selectedBoxColor)
        self.selectedBoxBrush.setStyle(self.boundingBoxPattern)

        self.cleaningOffset = int(self.json.get('cleaningOffset')) if self.json.get('cleaningOffset') else 2
        self.scanOffset = int(self.json.get('scanOffset')) if self.json.get('scanOffset') else 5
        self.removeScanImage = self.json.get('removeScanImage') if (self.json.get('removeScanImage') is not None) else True
        self.removeArchiveImage = self.json.get('removeArchiveImage') if (self.json.get('removeArchiveImage') is not None) else True
        self.inpaintOffset = int(self.json.get('inpaintOffset')) if self.json.get('inpaintOffset') else 2
        self.inpaintRadius = int(self.json.get('inpaintRadius')) if self.json.get('inpaintRadius') else 7

        self.inpaintMethod = eval(f"cv2.INPAINT_{self.json.get('inpaintMethod').upper()}") if self.json.get('inpaintMethod') else cv2.INPAINT_TELEA

        self.debug = self.json.get('debug') if (self.json.get('debug') is not None) else False

    @staticmethod
    def hex2int(s:str):
        """Hex to integer support method.

        Args:
            s (str): Hex string.

        Returns:
            Hex value as an integer.
        """
        return int(s.replace('0x','').replace('#',''), 16)

class RetCom(QtWidgets.QMainWindow):
    greenBrush = QtGui.QBrush(QtCore.Qt.green)
    redBrush = QtGui.QBrush(QtCore.Qt.red)
    magentaBrush = QtGui.QBrush(QtCore.Qt.magenta)
    blueBrush = QtGui.QBrush(QtCore.Qt.blue)
    blackBrush = QtGui.QBrush(QtCore.Qt.black)
    whiteBrush = QtGui.QBrush(QtCore.Qt.white)
    darkGreenBrush = QtGui.QBrush(QtCore.Qt.darkGreen)

    blackPen = QtGui.QPen(QtCore.Qt.black)
    blackPen.setWidth(5)

    noPen = QtGui.QPen(QtCore.Qt.black)
    noPen.setWidth(0)

    def __init__(self, imagePath, translator, parent=None):
        super(RetCom, self).__init__(parent=parent)

        self.translator:Translator = translator
        self.retcomconfig:RetComConfig = None
        self.imagePath = imagePath
        self.pilImage = Image.open(self.imagePath).convert('RGB')
        self.cvImage =  cv2.cvtColor(np.array(self.pilImage), cv2.COLOR_RGB2BGR)
        self.verticalText = True
        self.fontGeom:FontGeom = None
        # self.rects = []
        self.charAspectRatio = 0.95
        self.lengthBias = 1
        self.editToggle = False

        self.clickChanged = False
        self.editItem = None
        self.bboxes = []
        self.bells = []

        _, tail = os.path.split(self.imagePath)

        self.setWindowTitle(f'RetCom | {tail}')
        self.setGeometry(300, 200, 640, 520)
        self.createUI()
        self.createMenu()

        self.bboxSettings = BoundingBoxSettings(self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.bboxSettings)
        self.bboxSettings.setFloating(True)
        self.bboxSettings.adjustSize()
        # self.resizeDocks([self.bboxSettings], [0], QtCore.Qt.Horizontal)
        self.bboxSettings.show()

        self.scene.selectionChanged.connect(self.onSelectionChanged)

    @staticmethod
    def openRetCom(retcomconfig:RetComConfig, translator:Translator, directory=None):
        if not directory:
            directory = CWD
        path, _ = QtWidgets.QFileDialog.getOpenFileName(parent=None, caption='Choose Image/Archive', dir=directory, filter="Images/Archives (*.png *.jpg *.tif *.zip *.cbz *.rar *.cbr)")
        if path:
            if path.split('.')[-1].lower() in ['zip', 'cbz']:
                z = zipfile.ZipFile(path)
                options = sorted([f for f in z.namelist() if '__MACOSX' not in f])

                choice, resp = QtWidgets.QInputDialog.getItem(None, 'Files in archive', 'Choose file:', options)
                if choice:
                    fsrc = z.open(choice)
                    src = fsrc.read()
                    fsrc.close()

                    head, _ = os.path.split(path)
                    dst = os.path.normpath(os.path.join(head, 'rctemp_' + choice))
                    fdst = open(dst, 'wb')
                    fdst.write(src)
                    fdst.close()

                    path = dst
                else:
                    return
            elif path.split('.')[-1].lower() in ['rar', 'cbr']:
                z = rarfile.RarFile(path)
                options = sorted([f for f in z.namelist() if '__MACOSX' not in f])

                choice, resp = QtWidgets.QInputDialog.getItem(None, 'Files in archive', 'Choose file:', options)
                if choice:
                    fsrc = z.open(choice)
                    src = fsrc.read()
                    fsrc.close()

                    head, _ = os.path.split(path)
                    dst = os.path.normpath(os.path.join(head, 'rctemp_' + choice))
                    fdst = open(dst, 'wb')
                    fdst.write(src)
                    fdst.close()

                    path = dst
                else:
                    return
        
            # path = '../jpn.GenEiAntiquePv5.jpg'
            lang = retcomconfig.language
            # lang='en'

            retcom = RetCom(path, translator)
            retcom.retcomconfig = retcomconfig
            # print(retcomconfig.fontPath)
            # print(retcomconfig.boxPath)
            # print(os.path.join(retcomconfig.fontPath, 'GenEiAntiquePv5-M.ttf'))
            retcom.fontGeom = FontGeom(os.path.normpath(os.path.join(retcomconfig.fontPath, retcomconfig.font)))
            # retcom.verticalText = False
            if retcomconfig.doPrescan:
                retcom.parseLSTMBox(runTesseract(path, retcomconfig.tessdataPath, lang=lang, relPath=retcomconfig.boxPath))

            retcom.show()
        else:
            pass

    def createUI(self):
        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.setBackgroundBrush(QtGui.QColor(255, 255, 255, 0))

        self.image = QtGui.QPixmap(self.imagePath)
        self.imagePixmapItem = self.scene.addPixmap(self.image)
        self.imagePixmapItem.setZValue(-2)

        # self.simpleText = QtWidgets.QGraphicsSimpleTextItem('None')
        # self.simpleText = QtWidgets.QGraphicsTextItem(None)
        # self.simpleText.setHtml("<span style='background-color:white;color:black;'>None</span>")
        # font = self.simpleText.font()
        # font.setPointSize(18)
        # self.simpleText.setFont(font)
        # self.simpleText.setBackgroundBrush(self.whiteBrush)

        # self.scene.addItem(self.simpleText)

        # self.rect = BoundingBox(0,0, 200,200)
        # self.scene.addItem(self.rect)
        # self.rect.setPen(self.noPen)
        # self.rect.setBrush(self.redBrush)
        # self.rect.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        # self.rect.setOpacity(0.5)
        
        # self.rect = self.scene.addRect(0,0, 200,200, self.noPen, self.redBrush)
        # self.rect.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        # self.rect.setOpacity(0.5)

        

        self.view = QtWidgets.QGraphicsView(self.scene, self)
        self.setCentralWidget(self.view)
        self.view.setGeometry(0,0, 640,520)
        self.view.setBackgroundBrush(QtGui.QColor(255, 255, 255, 0))

        self.view.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemShape)
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        
        self.view.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.view.show()
        # self.view.fitInView(self.image.rect())

    def createMenu(self):
        menubar = self.menuBar()

        openRetComAction = QtWidgets.QAction('Open Image', self)
        openRetComAction.setShortcut('Ctrl+O')
        openRetComAction.setStatusTip('Open image')
        openRetComAction.triggered.connect(self.openRetComEvent)

        loadLSTMBoxAction = QtWidgets.QAction('Load LSTMBox', self)
        loadLSTMBoxAction.setShortcut('Ctrl+L')
        loadLSTMBoxAction.setStatusTip('Load LSTMBox')
        loadLSTMBoxAction.triggered.connect(self.loadLSTMBoxEvent)

        loadTXTEllAction = QtWidgets.QAction('Load TXTEll', self)
        loadTXTEllAction.setShortcut('Ctrl+Shift+L')
        loadTXTEllAction.setStatusTip('Load TXTEll')
        loadTXTEllAction.triggered.connect(self.loadTXTEllEvent)

        exportLSTMBoxAction = QtWidgets.QAction('Export LSTMBox', self)
        exportLSTMBoxAction.setShortcut('Ctrl+E')
        exportLSTMBoxAction.setStatusTip('Export LSTMBox')
        exportLSTMBoxAction.triggered.connect(self.exportLSTMBoxEvent)

        exportTXTEllAction = QtWidgets.QAction('Export TXTEll', self)
        exportTXTEllAction.setShortcut('Ctrl+Shift+E')
        exportTXTEllAction.setStatusTip('Export TXTEll')
        exportTXTEllAction.triggered.connect(self.exportTXTEllEvent)

        saveCleanedImageAction = QtWidgets.QAction('Save Cleaned Image', self)
        saveCleanedImageAction.setShortcut('Ctrl+S')
        saveCleanedImageAction.setStatusTip('Save cleaned image')
        saveCleanedImageAction.triggered.connect(self.saveCleanedImageEvent)

        saveScreenAction = QtWidgets.QAction('Save Screen', self)
        saveScreenAction.setShortcut('Ctrl+Shift+S')
        saveScreenAction.setStatusTip('Save screen')
        saveScreenAction.triggered.connect(self.saveScreenEvent)

        self.retcomMenu = menubar.addMenu('&RetCom')
        self.retcomMenu.addAction(openRetComAction)
        self.retcomMenu.addAction(saveCleanedImageAction)
        self.retcomMenu.addAction(saveScreenAction)
        self.retcomMenu.addAction(loadLSTMBoxAction)
        self.retcomMenu.addAction(loadTXTEllAction)
        self.retcomMenu.addAction(exportLSTMBoxAction)
        self.retcomMenu.addAction(exportTXTEllAction)

        translatePageAction = QtWidgets.QAction('Translate Page', self)
        translatePageAction.setShortcut('Ctrl+T')
        translatePageAction.setStatusTip('Translate current page')
        translatePageAction.triggered.connect(self.translatePageEvent)

        prescanAction = QtWidgets.QAction('Prescan Page', self)
        prescanAction.setShortcut('Ctrl+P')
        prescanAction.setStatusTip('Prescans the current page')
        prescanAction.triggered.connect(self.prescanEvent)

        infoAction = QtWidgets.QAction('Open Information', self)
        infoAction.setShortcut('Ctrl+I')
        infoAction.setStatusTip('Info on the current page')
        infoAction.triggered.connect(self.infoEvent)

        self.editMenu = menubar.addMenu('&Edit')
        self.editMenu.addAction(translatePageAction)
        self.editMenu.addAction(prescanAction)
        self.editMenu.addAction(infoAction)


    def exportLSTMBoxEvent(self):
        head, tail = os.path.split(self.imagePath)
        boxPathDir = os.path.join(head, self.retcomconfig.boxPath)
        boxPath = os.path.normpath(os.path.join(boxPathDir, tail))

        path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=None, caption='Export lstmbox', dir=boxPath+'.py.box', filter="Box files (*.box *.py.box)")
        if path != '':
            self.exportLSTMBox(path)

    def exportTXTEllEvent(self):
        head, tail = os.path.split(self.imagePath)
        boxPathDir = os.path.join(head, self.retcomconfig.boxPath)
        boxPath = os.path.normpath(os.path.join(boxPathDir, tail))

        path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=None, caption='Export txtell', dir=boxPath+'.py.ell', filter="Ellipse files (*.ell *.py.ell)")
        if path != '':
            self.exportTXTEll(path)

    def loadLSTMBoxEvent(self):
        imagePath, imageName = os.path.split(self.imagePath)
        boxPath = os.path.normpath(os.path.join(os.path.split(self.imagePath)[0], self.retcomconfig.boxPath))
        if os.path.exists(boxPath):
            boxFile = os.path.normpath(os.path.join(boxPath, imageName) + '.py.box')
            if os.path.exists(boxFile):
                defaultPath = boxFile
            else:
                defaultPath = boxPath
        else:
            defaultPath = imagePath
        
        path, _ = QtWidgets.QFileDialog.getOpenFileName(parent=None, caption='Choose LSTMBox', dir=defaultPath, filter="Box files (*.box *.py.box)")
        if path != '':
            self.parseLSTMBox(path)
        else:
            pass

    def loadTXTEllEvent(self):
        imagePath, imageName = os.path.split(self.imagePath)
        boxPath = os.path.normpath(os.path.join(os.path.split(self.imagePath)[0], self.retcomconfig.boxPath))
        if os.path.exists(boxPath):
            boxFile = os.path.normpath(os.path.join(boxPath, imageName) + '.py.box')
            if os.path.exists(boxFile):
                defaultPath = boxFile
            else:
                defaultPath = boxPath
        else:
            defaultPath = imagePath
        
        path, _ = QtWidgets.QFileDialog.getOpenFileName(parent=None, caption='Choose TXTEll', dir=defaultPath, filter="Ellpse files (*.ell *.py.ell)")
        if path != '':
            self.parseTXTEll(path)
        else:
            pass


    def prescanEvent(self):
        self.parseLSTMBox(runTesseract(self.imagePath, self.retcomconfig.tessdataPath, lang=self.retcomconfig.language, relPath=self.retcomconfig.boxPath))

    def infoEvent(self):
        self.infoDialog = InfoDialog(self)

        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.infoDialog)
        self.infoDialog.setFloating(True)
        self.infoDialog.adjustSize()
        self.infoDialog.show()

    def openRetComEvent(self):
        self.openRetCom(self.retcomconfig, self.translator, os.path.split(self.imagePath)[0])

    def makeCleanedImage(self):
        # Mask bboxes
        image = self.pilImage.copy()
        imageDraw = ImageDraw.Draw(image)

        offset = self.retcomconfig.cleaningOffset

        for bbox in self.bboxes:
            topLeft = bbox.sceneBoundingRect().topLeft()
            x = topLeft.x()
            y = topLeft.y()
            w = bbox.currentW
            h = bbox.currentH
            shape = [x-offset, y-offset, x+w+2*offset, y+h+2*offset]

            imageDraw.rectangle(shape, fill='white')

        cvImage = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # cv2.imshow('cvImage new', self.cvImage)

        # self.image.convertFromImage(ImageQt.ImageQt(self.pilImage))
        h, w, ch = self.cvImage.shape
        self.image.convertFromImage(QtGui.QImage(cvImage.data, w, h, 3*w, QtGui.QImage.Format_RGB888))
        self.imagePixmapItem.setPixmap(self.image)
        self.imagePixmapItem.update()

        # Overlay text
        self.scene.clearSelection()

        for bell in self.bells:
            bell.setSelected(True)
        
        for bbox in self.bboxes:
            bbox.setSelected(True)

        self.hideSelected()

        for _, group in BoundingBoxGroup.groups[self.scene].items():
            group.hide()

        self.scene.clearSelection()
        image = QtGui.QImage(self.view.sceneRect().size().toSize(), QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(image)
        self.scene.render(painter)
        painter.end()

        cvImage = convertQImageToCV2(image)

        self.unhideAll()

        # Restore original background
        self.image.convertFromImage(QtGui.QImage(self.cvImage.data, w, h, 3*w, QtGui.QImage.Format_RGB888))
        self.imagePixmapItem.setPixmap(self.image)
        self.imagePixmapItem.update()

        return convertCV2PIL(cvImage)

    def saveCleanedImageEvent(self):
        if self.bells is []:
            newFile = '.'.join(self.imagePath.split('.')[:-1]) + '.cleaned.' + self.imagePath.split('.')[-1]
        else:
            newFile = '.'.join(self.imagePath.split('.')[:-1]) + '.typeset.' + self.imagePath.split('.')[-1]

        path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=None, caption='Save cleaned image', dir=newFile, filter="Image files (*.png *.jpg *.tif)")
        if path != '':
            image = self.makeCleanedImage()
            image.save(path)
        else:
            pass

    def saveScreenEvent(self):
        newFile = '.'.join(self.imagePath.split('.')[:-1]) + '.screen.' + self.imagePath.split('.')[-1]

        path, _ = QtWidgets.QFileDialog.getSaveFileName(parent=None, caption='Save screen', dir=newFile, filter="Image files (*.png *.jpg *.tif)")
        if path != '':
            self.scene.clearSelection()

            for bell in self.bells:
                bell.setSelected(True)
            
            for bbox in self.bboxes:
                bbox.setSelected(True)

            self.hideSelected()
            self.scene.clearSelection()
            image = QtGui.QImage(self.view.sceneRect().size().toSize(), QtGui.QImage.Format_ARGB32)
            image.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter(image)
            self.scene.render(painter)
            painter.end()
            image.save(path)

            self.unhideAll()
        else:
            pass

    def translatePageEvent(self):
        self.translationDialog = TranslationDialog(self)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.translationDialog)
        self.translationDialog.setFloating(True)
        self.translationDialog.adjustSize()
        self.translationDialog.show()

    def parseLSTMBox(self, path):
        self.lstmbox = LSTMBox(path, self.verticalText)

        for val in self.lstmbox.boxList:
            txt = val[0]

            c = val[1]
            w = c[2]-c[0]
            h = c[3]-c[1]
            x, y = c[0], self.image.height()-c[3]

            n = c[4]

            if txt != '␟':
                if self.fontGeom:
                    if self.verticalText:
                        ar = self.fontGeom.getTextAspectRatio(txt)
                        bbox = BoundingBox(x,y, w,ar*w*self.lengthBias, self)
                    else:
                        ar = self.fontGeom.getTextAspectRatio(txt)
                        bbox = BoundingBox(x,y, ar*h*self.lengthBias,h, self)
                else:
                    if self.verticalText:
                        bbox = BoundingBox(x,y, w,self.charAspectRatio*w*len(txt)*self.lengthBias, self)
                    else:
                        bbox = BoundingBox(x,y, self.charAspectRatio*h*len(txt)*self.lengthBias,h, self)
            else:
                bbox = BoundingBox(x,y, w,h, self)

            bbox.actualW = w
            bbox.actualH = h

            bbox.setPen(self.noPen)
            if bbox.aspectRatio < self.retcomconfig.suspiciousAspectRatio:
                if txt != '␟':
                    bbox.setBrush(self.retcomconfig.flaggedBoxBrush)
                    bbox.flagged = True
            else:
                if txt != '␟':
                    bbox.setBrush(self.retcomconfig.boundingBoxBrush)
                else:
                    bbox.setBrush(self.retcomconfig.fillerBoxBrush)

            if self.retcomconfig.fullWidth:
                txt = half2fullWidth(txt)
            else:
                txt = full2halfWidth(txt)

            bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
            bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
            bbox.setOpacity(self.retcomconfig.boundingBoxOpacity)
            bbox.text = txt
            bbox.origText = txt

            self.bboxes.append(bbox)

            if n != 0:
                if BoundingBoxGroup.groups[self.scene][n]:
                    bbg = BoundingBoxGroup.groups[self.scene][n]
                    bbg.add(bbox)
                    bbg.updateShape()
                else:
                    while not BoundingBoxGroup.groups[self.scene][n]:
                        bbg = BoundingBoxGroup([], self.scene, self)
                        bbg.setBrush(self.retcomconfig.groupBoxBrush)
                        bbg.setOpacity(self.retcomconfig.groupBoxOpacity)
                        self.scene.addItem(bbg)

                    bbg.add(bbox)
                    bbg.updateShape

            # self.rects.append(bbox)
            self.scene.addItem(bbox)
            self.bboxSettings.bbTree.fillTree()

        # for c in lstmbox.boxCleaned:
        #     w = c[3]-c[1]
        #     x, y = c[1], self.image.height()-c[4]
        #     txt = lstmbox.boxStringDict[hash(tuple(c[1:-1]))]

        #     bbox = BoundingBox(x,y, w,w*len(txt))
        #     bbox.setPen(self.noPen)
        #     bbox.setBrush(self.redBrush)
        #     bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        #     bbox.setOpacity(0.5)
        #     bbox.text = txt

        #     self.rects.append(bbox)
        #     self.scene.addItem(bbox)

    def parseTXTEll(self, path):
        with open(path, encoding="utf8") as f:
            txtell = f.read()

        for info in txtell.split('::|--|::'):
            info_l = info.split('::||::')
            txt, size, family, x, y, w, h = info_l[0], int(info_l[1]), float(info_l[2]), float(info_l[3]), float(info_l[4]) , float(info_l[5])

            
            bell = BoundingEllipse(x,y, w,h, self)
            bell.setPen(self.noPen)
            bell.text = '␟'
            bell.origText = '␟'
            bell.flagged = False
            bell.updateFill()
            bell.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
            bell.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
            bell.setOpacity(self.retcomconfig.boundingBoxOpacity)
            bell.displayText = txt
            bell.fontSize = size
            bell.font.setFamily(family)
            bell.displayTextItem.setFont(bell.font)
            bell.alignContents()
            self.bells.append(bell)
            self.scene.addItem(bell)


    def createLSTMBox(self):
        lines = []
        h = self.image.height()
        accountedFor = []

        groups = BoundingBoxGroup.groups[self.scene]

        for n in sorted(list(groups.keys())):
            group = groups[n]

            for item in group.items:
                line = [0,0,0,0,0]
                rect = item.sceneBoundingRect()
                topLeft = rect.topLeft()
                line[0] = topLeft.x()
                line[3] = h - topLeft.y()
                line[1] = line[3] - rect.height()
                line[2] = line[0] + rect.width()

                line[4] = n

                line = [str(round(el)) for el in line]

                lines.append('\n'.join(' '.join([char] + line) for char in item.text))
                accountedFor.append(item)


        for item in self.bboxes:
            if item not in accountedFor:
                line = [0,0,0,0,0]
                topLeft = item.sceneBoundingRect().topLeft()
                line[0] = topLeft.x()
                line[3] = h - topLeft.y()
                line[1] = line[3] - item.rect().height()
                line[2] = line[0] + item.rect().width()

                line = [str(round(el)) for el in line]

                lines.append('\n'.join(' '.join([char] + line) for char in item.text))

                accountedFor.append(item)

        return '\n'.join(lines)

    def exportLSTMBox(self, path):
        lstmbox = self.createLSTMBox()

        with open(path, 'w+') as f:
            f.write(lstmbox)

    def exportTXTEll(self, path):
        txtell_l = []
        for bell in self.bells:
            info = '::||::'.join([bell.displayText, str(bell.fontSize), str(bell.font.family()), str(round(bell.sceneX)), str(round(bell.sceneY)), str(round(bell.currentW)), str(round(bell.currentH))])
            txtell_l.append(info)
        
        txtell = '::|--|::'.join(txtell_l)

        with open(path, 'w+') as f:
            f.write(txtell)

    def resizeEvent(self, event):
        self.view.setGeometry(0,0, self.width(), self.height())
        self.bboxSettings.adjustSize()

    def resizeSelectedUniformly(self, s=1):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox') or hasattr(item, 'isBell'):
                item.resize(item.rect().width()*s, item.rect().height()*s)

    @QtCore.Slot()
    def onSelectionChanged(self):
        for item in self.scene.items():
            if hasattr(item, 'isBbox') or hasattr(item, 'isBell'):
                item.updateFill()
                # if item in selectedItems:
                #     # print(f"{item.text} selected")
                #     item.setBrush(self.blueBrush)
                # elif ((item.aspectRatio < retcomconfig.suspiciousAspectRatio) and not item.flagged) or item.flagged: 
                #     item.setBrush(self.magentaBrush)
                # else:
                #     # print(f"{item.text} unselected")
                #     item.setBrush(self.redBrush)

        if len(self.scene.selectedItems()) == 1:
            for item in self.scene.selectedItems():
                if hasattr(item, 'isBbox'):
                    if item.treeItem:
                        self.bboxSettings.bbTree.scrollToItem(item.treeItem)
                        self.bboxSettings.bbTree.setCurrentItem(item.treeItem)
                    # self.simpleText.setHtml(f"<span style='background-color:white;color:black;'>{item.text}</span>")
                    # self.bboxSettings.bbText.setText(item.text)

    def removeSelected(self):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox'):
                self.scene.removeItem(item)
                self.bboxes.remove(item)
                if item.group:
                    group = item.group
                    item.group.remove(item)
                    group.updateShape()
            elif hasattr(item, 'isBell'):
                item.disband()
                self.scene.removeItem(item)
                self.bells.remove(item)

    def removeFlagged(self):
        for item in self.scene.items():
            if hasattr(item, 'isBbox'):
                if item.flagged:
                    self.scene.removeItem(item)
                    self.bboxes.remove(item)
                    if item.group:
                        group = item.group
                        item.group.remove(item)
                        group.updateShape()
            elif hasattr(item, 'isBell'):
                if item.flagged:
                    item.disband()
                    self.scene.removeItem(item)
                    self.bells.remove(item)

    def restoreSelected(self):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox'):
                item.setPos(item.origX, item.origY)
                item.updateContent(item.origText)
                if item.group:
                    item.group.updateShape()
            if hasattr(item, 'isBell'):
                item.setPos(item.origX, item.origY)

    def setFlagSelected(self, flag):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox'):
                item.flagged = flag
                # print(item.text, item.flagged)
                item.updateFill()

    def makeGroupFromSelected(self):
        bbg = BoundingBoxGroup(sorted(self.scene.selectedItems(), key=lambda x: self.bboxes.index(x)), self.scene, self)
        bbg.setBrush(self.retcomconfig.groupBoxBrush)
        bbg.setOpacity(self.retcomconfig.groupBoxOpacity)
        # bbg.setZValue(0)
        self.scene.addItem(bbg)
        # print(bbg.groups)

    def removeSelectedFromGroup(self):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox'):
                if item.group:
                    group = item.group
                    item.group = None
                    group.items.remove(item)
                    group.updateShape()

                    if len(group.items) == 0:
                        group.disband()


    def updateGroupBoundingRectSelected(self):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox'):
                if item.group:
                    item.group.updateShape()

    def convertToOutline(self, img, x=0, y=0):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imshow('gray', gray)
        ret, binary = cv2.threshold(gray,200,255,cv2.THRESH_BINARY)
        cv2.imshow('threshold', binary)
        # Closing
        kernel = np.ones((2,2),np.uint8)
        closing = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cv2.imshow('closing', closing)
        # Dilation
        kernel = np.ones((3,3),np.uint8)
        dilation = cv2.bitwise_not(cv2.dilate(cv2.bitwise_not(closing), kernel, iterations=2))
        cv2.imshow('dilation', dilation)
        # Opening
        # opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel)
        # cv2.imshow('opening', opening)
        # Erosion
        # kernel = np.ones((5,5),np.uint8)
        # erosion = cv2.erode(opening, kernel, iterations=1)
        # cv2.imshow('erosion', erosion)

        w, h = self.pilImage.size
        whiteBg = Image.new("RGB", (w, h))
        whiteBg.paste(convertCV2PIL(cv2.bitwise_not(dilation)), (round(x), round(y)))
        mask = cv2.cvtColor(convertPIL2CV(whiteBg), cv2.COLOR_BGR2GRAY)

        cv2.imshow('mask', mask)

        # print(fastInpaint(self.cvImage))

        maskCp = np.copy(mask)

        dst_telea = cv2.inpaint(self.cvImage,mask,7,cv2.INPAINT_TELEA)
        cv2.imshow('inpaint_telea',dst_telea)

        dst_ns = cv2.inpaint(self.cvImage,mask,7,cv2.INPAINT_NS)
        cv2.imshow('inpaint_ns',dst_ns)

        # dst_fdii = fastInpaint(self.cvImage, maskCp, None, 5)
        # cv2.imshow('inpaint_fdii',dst_fdii)

        return dst_telea

    def scanCroppedBox(self, x, y, w, h, offset):
        imageDir, imageName = os.path.split(self.imagePath)
        imageExtension = imageName.split('.')[-1]
        tmpDir = os.path.join(imageDir, '.retcom_tmp')
        tmpFile = os.path.normpath(os.path.join(tmpDir, str(uuid.uuid4()) + '.' + imageExtension))

        if not os.path.exists(tmpDir):
            os.makedirs(tmpDir)

        image = self.pilImage.crop((x-offset,y-offset, x+w+2*offset,y+h+2*offset))
        # convertCV2PIL(self.convertToOutline(convertPIL2CV(image), x-offset, y-offset))
        image.save(tmpFile)
        txt = runTesseractScan(tmpFile, self.retcomconfig.tessdataPath, lang=self.retcomconfig.language).decode('utf-8')
        txt = txt.strip().replace('\n', self.retcomconfig.collationString).replace(' ', '')
        
        if self.retcomconfig.removeScanImage:
            os.remove(tmpFile)

        return txt

    def inpaintSelection(self, offset, filterBlack=True):
        rect = self.view.mapToScene(self.view.rubberBandRect()).boundingRect()
        if (rect.width() > 0) and (rect.height() > 0):
            # anchor = self.view.mapToScene(QtCore.QPoint(rect.x(), rect.y()))
            topLeft = rect.topLeft()
            x,y, w,h = topLeft.x(),topLeft.y(), rect.width(),rect.height()

            img = convertPIL2CV(self.pilImage.crop((x-offset,y-offset, x+w+2*offset,y+h+2*offset)))

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # cv2.imshow('gray', gray)
            ret, binary = cv2.threshold(gray,200,255,cv2.THRESH_BINARY)
            if not filterBlack:
                binary = cv2.bitwise_not(binary)
            
            if self.retcomconfig.debug:
                cv2.imshow('threshold', binary)
            # Closing
            kernel = np.ones((2,2),np.uint8)
            closing = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            # cv2.imshow('closing', closing)
            # Dilation
            kernel = np.ones((3,3),np.uint8)
            dilation = cv2.bitwise_not(cv2.dilate(cv2.bitwise_not(closing), kernel, iterations=2))
            if self.retcomconfig.debug:
                cv2.imshow('dilation', dilation)

            W, H = self.pilImage.size
            whiteBg = Image.new("RGB", (W, H))
            whiteBg.paste(convertCV2PIL(cv2.bitwise_not(dilation)), (round(x), round(y)))
            mask = cv2.cvtColor(convertPIL2CV(whiteBg), cv2.COLOR_BGR2GRAY)
            # cv2.imshow('mask', mask)

            dst = cv2.inpaint(self.cvImage,mask,self.retcomconfig.inpaintRadius,self.retcomconfig.inpaintMethod)

            self.pilImage = convertCV2PIL(dst)
            self.cvImage = cv2.cvtColor(np.array(self.pilImage), cv2.COLOR_RGB2BGR)

            # cv2.imshow('cvImage new', self.cvImage)

            # self.image.convertFromImage(ImageQt.ImageQt(self.pilImage))
            h, w, ch = self.cvImage.shape
            self.image.convertFromImage(QtGui.QImage(self.cvImage.data, w, h, 3*w, QtGui.QImage.Format_RGB888))
            self.imagePixmapItem.setPixmap(self.image)
            self.imagePixmapItem.update()


    def scanSelectionAndMakeBBox(self, offset):
        rect = self.view.mapToScene(self.view.rubberBandRect()).boundingRect()
        if (rect.width() > 0) and (rect.height() > 0):
            # anchor = self.view.mapToScene(QtCore.QPoint(rect.x(), rect.y()))
            topLeft = rect.topLeft()
            x,y, w,h = topLeft.x(),topLeft.y(), rect.width(),rect.height()

            txt = self.scanCroppedBox(x,y, w,h, offset)

            bbox = BoundingBox(x,y, w,h, self)
            bbox.setPen(self.noPen)
            bbox.text = '␟'
            bbox.origText = '␟'
            bbox.flagged = False

            bbox.updateContent(txt)
            bbox.updateFill()
            bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
            bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
            bbox.setOpacity(self.retcomconfig.boundingBoxOpacity)
            self.scene.addItem(bbox)
            bbox.setSelected(True)
            self.bboxes.append(bbox)
        else:
            selectedItems = self.scene.selectedItems()
            for item in selectedItems:
                if hasattr(item, 'isBbox'):
                    rect = item.sceneBoundingRect()
                    topLeft = rect.topLeft()
                    x,y, w,h = topLeft.x(),topLeft.y(), rect.width(),rect.height()

                    txt = self.scanCroppedBox(x,y, w,h, offset)
                    
                    item.updateContent(txt)
                    item.updateFill()

            if len(selectedItems) == 1:
                selectedItems[0].setSelected(True)

        self.bboxSettings.bbTree.fillTree()


    def displaceSelected(self, direction, amount):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBbox') or hasattr(item, 'isBell'):
                item.moveBy(direction[0]*amount, direction[1]*amount)

    def hideSelected(self):
        selectedItems = self.scene.selectedItems()
        for item in selectedItems:
            if hasattr(item, 'isBell') or hasattr(item, 'isBbox') or hasattr(item, 'isBboxGroup'):
                item.hide()
                if hasattr(item, 'isBbox') and item.group:
                    item.group.hide()

    def hideAll(self):
        for item in self.scene.items():
            if hasattr(item, 'isBell') or hasattr(item, 'isBbox') or hasattr(item, 'isBboxGroup'):
                item.hide()

        for _, group in BoundingBoxGroup.groups[self.scene].items():
            group.hide()

    def unhideAll(self):
        for item in self.scene.items():
            if hasattr(item, 'isBell') or hasattr(item, 'isBbox') or hasattr(item, 'isBboxGroup'):
                item.show()

        # for bell in self.bells:
        #     bell.show()

        # for bbox in self.bboxes:
        #     bbox.show()

        # for _, group in BoundingBoxGroup.groups[self.scene].items():
        #     group.show()

    def keyPressEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        # REMOVE / REMOVE FLAGGED
        if event.key() in {QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace, QtCore.Qt.Key_D}:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.removeFlagged()
            else:
                self.removeSelected()

            self.bboxSettings.bbTree.fillTree()
        # RESTORE SELECTED
        elif event.key() == QtCore.Qt.Key_R:
            self.restoreSelected()
            self.bboxSettings.bbTree.fillTree()
        # FLAG / UNFLAG
        elif event.key() == QtCore.Qt.Key_F:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.setFlagSelected(False)
            else:
                self.setFlagSelected(True)
        # EDIT BBOX
        elif event.key() == QtCore.Qt.Key_E:
            if self.editToggle:
                rect = self.view.mapToScene(self.view.rubberBandRect()).boundingRect()
                if (rect.width() > 0) and (rect.height() > 0) and self.editItem:
                    item = self.editItem

                    w, h = rect.width(), rect.height()
                    topLeft = rect.topLeft()
                    x, y = topLeft.x(), topLeft.y()

                    item.setPos(x, y)
                    item.resize(w, h)
                
                self.editToggle = False
            else:
                selectedItems = self.scene.selectedItems()
                if len(selectedItems) == 1:
                    item = selectedItems[0]
                    if hasattr(item, 'isBbox') or hasattr(item, 'isBell'):
                        self.editItem = item
                    else:
                        self.editItem = None

                self.editToggle = True
        # ADD BBOX / SELECT ALL
        elif event.key() == QtCore.Qt.Key_A:
            if modifiers == QtCore.Qt.ShiftModifier:
                for item in self.scene.items():
                    item.setSelected(True)
            else:
                rect = self.view.mapToScene(self.view.rubberBandRect()).boundingRect()
                if (rect.width() > 0) and (rect.height() > 0):
                    # anchor = self.view.mapToScene(QtCore.QPoint(rect.x(), rect.y()))
                    topLeft = rect.topLeft()
                    bbox = BoundingBox(topLeft.x(),topLeft.y(), rect.width(),rect.height(), self)
                    bbox.setPen(self.noPen)
                    bbox.text = '␟'
                    bbox.origText = '␟'
                    bbox.flagged = False
                    bbox.updateFill()
                    bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
                    bbox.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
                    bbox.setOpacity(self.retcomconfig.boundingBoxOpacity)
                    self.scene.addItem(bbox)
                    bbox.setSelected(True)
                    self.bboxes.append(bbox)

                self.bboxSettings.bbTree.fillTree()
        # ADD ELLIPSE
        elif event.key() == QtCore.Qt.Key_T:
            rect = self.view.mapToScene(self.view.rubberBandRect()).boundingRect()
            if (rect.width() > 0) and (rect.height() > 0):
                # anchor = self.view.mapToScene(QtCore.QPoint(rect.x(), rect.y()))
                topLeft = rect.topLeft()
                bell = BoundingEllipse(topLeft.x(),topLeft.y(), rect.width(),rect.height(), self)
                bell.setPen(self.noPen)
                bell.text = '␟'
                bell.origText = '␟'
                bell.flagged = False
                bell.updateFill()
                bell.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
                bell.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
                bell.setOpacity(self.retcomconfig.boundingBoxOpacity)
                self.scene.addItem(bell)
                bell.setSelected(True)
                bell.changeTextEvent()
                self.bells.append(bell)
        # HIDE ELLIPSE
        elif event.key() == QtCore.Qt.Key_H:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.unhideAll()
            else:
                self.hideSelected()
        # GROUP / UNGROUP
        elif event.key() == QtCore.Qt.Key_G:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.removeSelectedFromGroup()
            else:
                self.makeGroupFromSelected()

            self.bboxSettings.bbTree.fillTree()
        # SCAN SELECTION AND MAKE BBOX
        elif event.key() == QtCore.Qt.Key_S:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.scanSelectionAndMakeBBox(0)
            else:
                self.scanSelectionAndMakeBBox(self.retcomconfig.scanOffset)
        # INPAINT
        elif event.key() == QtCore.Qt.Key_W:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.inpaintSelection(0, False)
            else:
                self.inpaintSelection(0, True)
                # self.inpaintSelection(self.retcomconfig.inpaintOffset)
        # NUDGE
        elif event.key() == QtCore.Qt.Key_I:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.displaceSelected([0,-1], self.retcomconfig.fineNudgeAmount)
            else:
                self.displaceSelected([0,-1], self.retcomconfig.nudgeAmount)

            self.updateGroupBoundingRectSelected()
        elif event.key() == QtCore.Qt.Key_J:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.displaceSelected([-1,0], self.retcomconfig.fineNudgeAmount)
            else:
                self.displaceSelected([-1,0], self.retcomconfig.nudgeAmount)

            self.updateGroupBoundingRectSelected()
        elif event.key() == QtCore.Qt.Key_L:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.displaceSelected([1,0], self.retcomconfig.fineNudgeAmount)
            else:
                self.displaceSelected([1,0], self.retcomconfig.nudgeAmount)
            
            self.updateGroupBoundingRectSelected()
        elif event.key() == QtCore.Qt.Key_K:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.displaceSelected([0,1], self.retcomconfig.fineNudgeAmount)
            else:
                self.displaceSelected([0,1], self.retcomconfig.nudgeAmount)

            self.updateGroupBoundingRectSelected()
        # ASPECT RATIO-PRESERVING RESIZE
        elif event.key() == QtCore.Qt.Key_BracketRight:
            self.resizeSelectedUniformly(1 + self.retcomconfig.scaleMultiplier)
            self.updateGroupBoundingRectSelected()
        elif event.key() == QtCore.Qt.Key_BraceRight:
            self.resizeSelectedUniformly(1 + self.retcomconfig.fineScaleMultiplier)
            self.updateGroupBoundingRectSelected()
        elif event.key() == QtCore.Qt.Key_BracketLeft:
            self.resizeSelectedUniformly(1 - self.retcomconfig.scaleMultiplier)
            self.updateGroupBoundingRectSelected()
        elif event.key() == QtCore.Qt.Key_BraceLeft:
            self.resizeSelectedUniformly(1 - self.retcomconfig.fineScaleMultiplier)
            self.updateGroupBoundingRectSelected()
        # SCENE ZOOM
        elif event.key() == QtCore.Qt.Key_Equal:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.view.scale(1 + self.retcomconfig.fineScaleMultiplier, 1 + self.retcomconfig.fineScaleMultiplier)
            else:
                self.view.scale(1 + self.retcomconfig.scaleMultiplier, 1 + self.retcomconfig.scaleMultiplier)
        elif event.key() == QtCore.Qt.Key_Minus:
            if modifiers == QtCore.Qt.ShiftModifier:
                self.view.scale(1 - self.retcomconfig.fineScaleMultiplier, 1 - self.retcomconfig.fineScaleMultiplier)
            else:
                self.view.scale(1 - self.retcomconfig.scaleMultiplier, 1 - self.retcomconfig.scaleMultiplier)

    def checkLSTMBoxChange(self):
        head, tail = os.path.split(self.imagePath)
        boxPathDir = os.path.join(head, self.retcomconfig.boxPath)
        boxPath = os.path.normpath(os.path.join(boxPathDir, tail))

        try:
            with open(boxPath + '.py.box', 'r', encoding="utf8") as f:
                current = f.read()

            new = self.createLSTMBox()

            if len(new.encode('utf-8')) <= self.retcomconfig.changeCheckThreshold:
                if new != current:
                    return ''.join(difflib.ndiff(current.splitlines(1), new.splitlines(1))), True
                else:
                    return '', False
            else:
                return 'File size exceeds checking threshold; contents might not have changed.', True
        except OSError:
            return 'New file.', True

    def closeEvent(self, event):
        event.ignore()

        diff, hasChanged = self.checkLSTMBoxChange()

        if hasChanged:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("The document has been modified.")
            msgBox.setInformativeText("Do you want to save your changes?")
            msgBox.setDetailedText(diff)
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Save)
            msgBox.setStyleSheet( "QMessageBox QTextEdit { font-family: 'Noto Sans Mono', 'Courier', 'Courier New'; }")
            ret = msgBox.exec_()

            if ret == QtWidgets.QMessageBox.Save:
                self.exportLSTMBoxEvent()
                if self.retcomconfig.removeScanImage and ('rctemp_' in self.imagePath):
                    os.remove(self.imagePath)

                event.accept()
            elif ret == QtWidgets.QMessageBox.Discard:
                if self.retcomconfig.removeScanImage and ('rctemp_' in self.imagePath):
                    os.remove(self.imagePath)

                event.accept()
            elif ret == QtWidgets.QMessageBox.Cancel:
                pass
        else:
            if (QtWidgets.QMessageBox.Yes == QtWidgets.QMessageBox.question(self, "RetCom | Close confirmation", "Are you sure you want to close this window?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)):
                if self.retcomconfig.removeScanImage and ('rctemp_' in self.imagePath):
                    os.remove(self.imagePath)

                event.accept()

    # def mousePressEvent(self, event):
    #     pos = event.pos()
    #     print(pos, self.rect.mapFromScene(pos))
    #     if self.rect.contains(self.rect.mapFromScene(pos)):
    #         print('In', event.pos())

class BoundingBox(QtWidgets.QGraphicsRectItem):
    def __init__(self, x=0, y=0, w=100, h=100, parent=None):
        super(BoundingBox, self).__init__(0,0, w,h)
        self.setPos(x, y)

        self.group = None
        self.treeItem = None 

        self.actualW = w
        self.actualH = h

        self.currentW = w
        self.currentH = h

        self.origX = x
        self.origY = y
        self.origW = w
        self.origH = h

        self.isBbox = True
        self.flagged = False

        self.parent = parent

        self.origText = None
        self.text = None

        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

        # self.handle = BoundingBoxHandle(parent=self)
        # self.handle.resizeSignal.connect(self.resize)
        # self.parent.scene.addItem(self.handle)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, txt):
        self._text = txt

        if txt == '␟':
            self.setZValue(0)
        else:
            self.setZValue(-1)

    @property
    def aspectRatio(self):
        # h = self.origH
        h = self.actualH

        # w = self.origW
        w = self.actualW

        if self.parent.verticalText:
            return self.origH/self.origW
        else:
            return self.origW/self.origH

    def removeSelected(self):
        self.parent.scene.removeItem(self)

        selectedItems = self.parent.scene.selectedItems()
        if len(selectedItems) > 1:
            for item in self.parent.scene.items():
                if hasattr(item, 'isBbox'):
                    if item in selectedItems:
                        self.parent.scene.removeItem(item)
                        self.parent.bboxes.remove(item)
                        if item.group:
                            group = item.group
                            item.group.remove(item)
                            group.updateShape()

    def restoreSelected(self):
        self.setPos(self.origX, self.origY)
        if self.group:
            self.group.updateShape()

        selectedItems = self.parent.scene.selectedItems()
        if len(selectedItems) > 1:
            for item in self.parent.scene.items():
                if hasattr(item, 'isBbox'):
                    if item in selectedItems:
                        item.setPos(item.origX, item.origY)
                        item.updateContent(item.origText)
                        item.updateFill()


    def mousePressEvent(self, event):
        self.parent.clickChanged = True
        
        if event.button() == QtCore.Qt.LeftButton:
            # self.parent.simpleText.setHtml(f"<span style='background-color:white;color:black;'>{self.text}</span>")
            # self.parent.bboxSettings.bbText.setText(self.text)
            if self.treeItem:
                self.parent.bboxSettings.bbTree.scrollToItem(self.treeItem)
                self.parent.bboxSettings.bbTree.setCurrentItem(self.treeItem)
            # self.parent.simpleText.setText(self.text)
            # print(f"{self.text}; {event.pos().x(), event.pos().y()}")
        # elif event.button() == QtCore.Qt.RightButton:
        #     self.removeSelected()
        elif event.button() == QtCore.Qt.MiddleButton:
            self.restoreSelected()
            # self.setRect(self.origX, self.origX, self.origW, self.origH)
            # print(self.origX, self.origY)
            # print(self.pos())
            # print(self.scenePos())

    def updateContent(self, txt):
        if self.parent.retcomconfig.fullWidth:
            txt = half2fullWidth(txt)
        else:
            txt = full2halfWidth(txt)

        if txt != '␟':
            rc = self.parent

            if rc.fontGeom:
                ar = rc.fontGeom.getTextAspectRatio(txt)*rc.lengthBias
            else:
                ar = rc.charAspectRatio*len(txt)*rc.lengthBias

            self.text = txt

            if rc.verticalText:
                w = self.rect().width()
                self.resize(w, ar*w)
            else:
                h = self.rect().height()
                self.resize(ar*h, h)
        else:
            self.text = txt

    def updateFill(self):
        if self.isSelected():
            self.setBrush(self.parent.retcomconfig.selectedBoxBrush)
        else:
            if self.text == '␟':
                self.setBrush(self.parent.retcomconfig.fillerBoxBrush)
            elif self.flagged: 
                self.setBrush(self.parent.retcomconfig.flaggedBoxBrush)
            else:
                self.setBrush(self.parent.retcomconfig.boundingBoxBrush)


    def resize(self, w, h):
        self.currentW = w
        self.currentH = h

        self.prepareGeometryChange()
        self.setRect(self.rect().adjusted(0,0, w-self.rect().width(),h-self.rect().height()))
        self.update()

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            # print('item pos change')
            if self.group:
                # print('updating shape...')
                self.group.updateShape()

        return value

class BoundingBoxGroup(QtWidgets.QGraphicsRectItem):
    groupNo = defaultdict(lambda: 1)
    groups = defaultdict(lambda: defaultdict(lambda: None))

    def __init__(self, items:[QtWidgets.QGraphicsItem], scene:QtWidgets.QGraphicsScene, parent=None):
        super(BoundingBoxGroup, self).__init__(0,0, 1,1)

        self.isBboxGroup = True

        self.items = items
        for item in items:
            if hasattr(item, 'isBbox'):
                item.group = self

        # self.group = scene.createItemGroup(items)
        self.scene = scene
        self.parent = parent
        self.treeItem = None

        self.updateShape()

        # self.setPen(self.parent.blackPen)
        self.setBrush(QtGui.QColor(255, 255, 255, 0))
        self.setZValue(1)

        self.number = self.groupNo[self.scene]
        self.groupNo[self.scene] += 1

        self.groups[self.scene][self.number] = self

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()

        groupAction = QtWidgets.QAction(f'Select G{self.number}', self.parent)
        groupAction.setStatusTip('Select group members')
        groupAction.triggered.connect(self.selectGroupMembers)

        collateTextAction = QtWidgets.QAction('Collate', self.parent)
        collateTextAction.setStatusTip('Collate text')
        collateTextAction.triggered.connect(self.collateTextEvent)

        translateTextAction = QtWidgets.QAction('Translate', self.parent)
        translateTextAction.setStatusTip('Translate text')
        translateTextAction.triggered.connect(self.translateTextEvent)

        menu.addAction(groupAction)
        menu.addAction(collateTextAction)
        menu.addAction(translateTextAction)
        menu.exec_(event.screenPos())

    def collateTextEvent(self):
        lines = []
        for bbox in self.items:
            text = bbox.text
            if text != '␟':
                lines.append(text)

        line = self.parent.retcomconfig.collationString.join(lines)

        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(line)
        msgBox.setWindowTitle(f'G{self.number} collated text')
        msgBox.exec_()

    def translateTextEvent(self):
        lines = []
        for bbox in self.items:
            text = bbox.text
            if text != '␟':
                lines.append(text)

        line = self.parent.retcomconfig.collationString.join(lines)

        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(self.parent.translator.translate(line, detailed=True, target=self.parent.retcomconfig.translationLanguage)['resp'])
        msgBox.setDetailedText(line)
        msgBox.setWindowTitle(f'G{self.number} translated text')
        msgBox.exec_()

    def selectGroupMembers(self):
        for item in self.items:
            item.setSelected(True)
        
        # infinite recursion!!!
        # if self.treeItem:
        #     self.parent.bboxSettings.bbTree.scrollToItem(self.treeItem)
        #     self.parent.bboxSettings.bbTree.setCurrentItem(self.treeItem)

    def boundingRect(self):
        rect = QtCore.QRectF()
        for item in self.items:
            rect = rect.united(item.sceneBoundingRect())

        # print(rect)

        return rect


    def updateShape(self):
        bRect = self.boundingRect()
        cRect = self.rect()
        self.prepareGeometryChange()
        # self.setRect(cRect.adjusted(bRect.x() - cRect.x(),bRect.y() - cRect.y(), bRect.width() - cRect.width(),bRect.height() - cRect.height()))
        self.setRect(bRect)
        self.update()
        self.scene.update()
        
    def add(self, item):
        self.items.append(item)
        item.group = self

    def remove(self, item):
        self.items.remove(item)
        item.group = None

    def disband(self):
        self.groups[self.scene][self.number] = None
        self.scene.removeItem(self)

class BoundingBoxTree(QtWidgets.QTreeWidget):
    def __init__(self, parent):
        super(BoundingBoxTree, self).__init__(parent)

        self.parent = parent
        self.fillTree()
        # self.defaultColor = QtWidgets.QApplication.palette().text().color()
        # self.defaultBrush = self.headerItem().backgroundColor(0)
        self.defaultBrush = QtGui.QColor(255, 255, 255, 0)
        self.setEditTriggers(QtWidgets.QTreeWidget.NoEditTriggers)
        self.setSelectionMode(self.SingleSelection)
        # self.setDragEnabled(True)
        self.setDragDropOverwriteMode(False)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        # self.setAcceptDrops(False)
        # self.setDropIndicatorShown(True)
        # self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        self.currentItemChanged.connect(self.onItemChange)
        self.itemDoubleClicked.connect(self.onItemDoubleClicked)
        self.currentItemChanged.connect(self.onCurrentItemChange)

    def textBackgroundColor(self, txt, flagged=False):
        if flagged:
            flaggedColor = self.parent.retcomconfig.flaggedBoxColor
            return QtGui.QColor(flaggedColor.red(), flaggedColor.green(), flaggedColor.blue(), round(self.parent.retcomconfig.boundingBoxOpacity*255))
        elif txt == '␟':
            fillerColor = self.parent.retcomconfig.fillerBoxColor
            return QtGui.QColor(fillerColor.red(), fillerColor.green(), fillerColor.blue(), round(self.parent.retcomconfig.boundingBoxOpacity*255))
        elif (txt[:2] == '[[') and (txt[-2:] == ']]'):
            groupColor = self.parent.retcomconfig.groupBoxColor
            return QtGui.QColor(groupColor.red(), groupColor.green(), groupColor.blue(), round(self.parent.retcomconfig.groupBoxOpacity*255))
        else:
            boundingColor = self.parent.retcomconfig.boundingBoxColor
            return QtGui.QColor(boundingColor.red(), boundingColor.green(), boundingColor.blue(), round(self.parent.retcomconfig.boundingBoxOpacity*255))
            # return self.defaultBrush

    def fillTree(self):
        self.clear()

        accountedFor = []
        # print('*****')
    
        for groupNo in sorted(list(BoundingBoxGroup.groups[self.parent.scene].keys())):
            if BoundingBoxGroup.groups[self.parent.scene][groupNo]:
                bbgTreeItem = QtWidgets.QTreeWidgetItem(self)
                text = f'[[G{groupNo}]]'
                bbgTreeItem.setText(0, text)
                bbgTreeItem.setFlags(bbgTreeItem.flags() | QtCore.Qt.ItemIsDropEnabled)
                bbgTreeItem.setBackground(0, self.textBackgroundColor(text))

                BoundingBoxGroup.groups[self.parent.scene][groupNo].treeItem = bbgTreeItem
                for item in BoundingBoxGroup.groups[self.parent.scene][groupNo].items:
                    # print(groupNo, item.text)
                    bboxTreeItem = QtWidgets.QTreeWidgetItem(bbgTreeItem)
                    bboxTreeItem.setText(0, item.text)
                    bboxTreeItem.setBackground(0, self.textBackgroundColor(item.text, item.flagged))
                    item.treeItem = bboxTreeItem
                    bboxTreeItem.setFlags(bboxTreeItem.flags() | QtCore.Qt.ItemIsEditable)
                    bboxTreeItem.setFlags(bboxTreeItem.flags() | QtCore.Qt.ItemIsDragEnabled)
                    accountedFor.append(item)

        # print('-----')

        for item in self.parent.bboxes:
            if item not in accountedFor:
                # print(item.text)
                bboxTreeItem = QtWidgets.QTreeWidgetItem(self)
                bboxTreeItem.setText(0, item.text)
                bboxTreeItem.setBackground(0, self.textBackgroundColor(item.text, item.flagged))
                item.treeItem = bboxTreeItem
                bboxTreeItem.setFlags(bboxTreeItem.flags() | QtCore.Qt.ItemIsEditable)
                bboxTreeItem.setFlags(bboxTreeItem.flags() | QtCore.Qt.ItemIsDragEnabled)
                accountedFor.append(item)

    def dropEvent(self, event:QtGui.QDropEvent):
        # print(event.proposedAction())
        # print(event.posF())
        # print(self.itemAt(event.pos()))
        # print(self.itemAt(event.pos()).text(0))
        source:QtWidgets.QTreeWidgetItem = self.currentItem()
        dest:QtWidgets.QTreeWidgetItem = self.itemAt(event.pos())

        if id(source) != id(dest):
            # print('BEFORE')
            # print([el.text for el in self.parent.bboxes])
            # print(source)
            sourceType, sourceBB = self.getBBObjectFromItem(source)
            if sourceType == 'bbg':
                return
            else:
                sourceBB:BoundingBox = sourceBB

            # dest is an item
            if dest:
                # print(source.text(0), dest.text(0))
                destType, destBB = self.getBBObjectFromItem(dest)
                # dest is BoundingBoxGroup
                if destType == 'bbg':
                    destBB:BoundingBoxGroup = destBB
                    sourceGroup = sourceBB.group
                    if sourceGroup:
                        sourceGroup.remove(sourceBB)

                    sourceBB.group = destBB
                    destBB.items = [sourceBB] + destBB.items
                    destBB.updateShape()

                    # print([hex(id(el)) for el in self.parent.bboxes])
                    # print(hex(id(destBB.items[0])))
                    # print(hex(id(sourceBB)))

                    self.parent.bboxes = self.insertBefore(self.parent.bboxes, destBB.items[0], sourceBB)
                # dest is BoundingBox
                else:
                    destBB:BoundingBox = destBB
                    destGroup:BoundingBoxGroup = destBB.group
                    
                    # dest has group
                    if destGroup:
                        sourceGroup = sourceBB.group
                        # different groups
                        if sourceGroup != destGroup:
                            if sourceGroup:
                                sourceGroup.remove(sourceBB)

                            sourceBB.group = destGroup
                            
                        # idxOfDest = destGroup.items.index(destBB)
                        self.parent.bboxes = self.insertBefore(self.parent.bboxes, destBB, sourceBB)
                        # print('BEFORE (dest w/ group)')
                        # print([el.text for el in destGroup.items])

                        destGroup.items = self.insertBefore(destGroup.items, destBB, sourceBB)

                        # print('AFTER (dest w/ group)')
                        # print([el.text for el in destGroup.items])
                        # destGroup.items.insert(min(0, idxOfDest-1), sourceBB)
                        
                        destGroup.updateShape()

                    # dest has no group
                    else:
                        sourceGroup:BoundingBoxGroup = sourceBB.group
                        if sourceGroup:
                            sourceGroup.remove(sourceBB)
                            sourceGroup.updateShape()

                        self.parent.bboxes = self.insertBefore(self.parent.bboxes, destBB, sourceBB)
            # dest is root
            else:
                # print(source.text(0), None)
                sourceGroup:BoundingBoxGroup = sourceBB.group
                if sourceGroup:
                    sourceGroup.remove(sourceBB)
                    sourceGroup.updateShape()
                
            # print('AFTER')
            # print([el.text for el in self.parent.bboxes])
            
            self.fillTree()

            selectedItems = self.parent.scene.selectedItems()
            if len(selectedItems) == 1:
                if selectedItems[0].treeItem:
                    self.parent.bboxSettings.bbTree.scrollToItem(selectedItems[0].treeItem)
                    self.parent.bboxSettings.bbTree.setCurrentItem(selectedItems[0].treeItem)
            elif len(selectedItems) > 1:
                if selectedItems[0].group:
                    if selectedItems[0].group.treeItem:
                        self.parent.bboxSettings.bbTree.scrollToItem(selectedItems[0].group.treeItem)
                        self.parent.bboxSettings.bbTree.setCurrentItem(selectedItems[0].group.treeItem)

    def getBBObjectFromItem(self, item):
        if item.parent():
            try:
                groupNo = int(item.parent().text(0).replace('[[', '').replace(']]', '').replace('G', ''))
            except ValueError:
                groupNo = None

            if groupNo:
                group = BoundingBoxGroup.groups[self.parent.scene][groupNo]
                bbox = None
                for bboxCandidate in group.items:
                    if id(bboxCandidate.treeItem) == id(item):
                        bbox = bboxCandidate
                        break

                return 'bbox', bbox
        else:
            try:
                groupNo = int(item.text(0).replace('[[', '').replace(']]', '').replace('G', ''))
            except ValueError:
                groupNo = None

            if groupNo:
                group = BoundingBoxGroup.groups[self.parent.scene][groupNo]

                return 'bbg', group
            else:
                bbox = None
                for bboxCandidate in self.parent.bboxes:
                    if id(bboxCandidate.treeItem) == id(item):
                        bbox = bboxCandidate
                        break

                return 'bbox', bbox

    @staticmethod
    def indexById(l, a):
        hid = hex(id(a))

        for idx, el in enumerate(l):
            if hex(id(el)) == hid:
                return idx

        return None

    # @staticmethod
    # def insertBefore(l, a, b):
    #     ib = BoundingBoxTree.indexById(l, b)
    #     l.remove(b)
    #     ia = BoundingBoxTree.indexById(l, a)
    #     if ia:
    #         if ia >= ib-1:
    #             l.insert(ia, b)
    #         else:
    #             l.insert(min(0, ia-1), b)
    #     else:
    #         l.insert(ib, b)
        
    #     return l

    @staticmethod
    def insertBefore(l, a, b):
        ia = l.index(a)
        try:
            ib = l.index(b)
        except ValueError:
            l.insert(ia, b)
        else:
            if ia > ib:
                pass
            elif ia < ib:
                if b in l:
                    l.remove(b)

                l.insert(ia, b)
                    
        return l

    @staticmethod
    def swapItemsInList(l, a, b):
        ia, ib = l.index(a), l.index(b)
        l[ia] = b
        l[ib] = a

        return l
        

    @QtCore.Slot()
    def onItemChange(self):
        item = self.currentItem()

        if item:
            self.parent.scene.clearSelection()

            if item.parent():
                group = BoundingBoxGroup.groups[self.parent.scene][int(item.parent().text(0).replace('[[', '').replace(']]', '').replace('G', ''))]
                bbox = group.items[item.parent().indexOfChild(item)]
                bbox.setSelected(True)
            else:
                txt = item.text(0)
                if (txt[:2] == '[[') and (txt[-2:] == ']]'):
                    group = BoundingBoxGroup.groups[self.parent.scene][int(item.text(0).replace('[[', '').replace(']]', '').replace('G', ''))]
                    group.selectGroupMembers()
                else:
                    bbType, bbox = self.getBBObjectFromItem(item)
                    
                    if bbox:
                        if bbType == 'bbox':
                            bbox:BoundingBox = bbox
                            # bboxesGroupless = [el for el in self.parent.bboxes if not el.group]
                            # print(self.topLevelItem(0).indexOfChild(item), BoundingBoxGroup.groupNo[self.parent.scene])
                            # bbox = bboxesGroupless[self.topLevelItem(0).indexOfChild(item) + BoundingBoxGroup.groupNo[self.parent.scene]]
                            # print(bbox.text)
                            bbox.setSelected(True)

        self.viewport().update()

    @QtCore.Slot()
    def onItemDoubleClicked(self, item, column):
        if item.parent():
            if column == 0:
                self.editItem(item, column)
        else:
            if column == 0 and item.text(0)[:2] != '[[' and item.text(0)[-2:] != ']]':
                self.editItem(item, column)

    # def mousePressEvent(self, event):
    #     if event.button() == QtCore.Qt.RightButton:
    #         item = self.currentItem()
    #         if item:
    #             txt = item.text(0)
    #             if (txt[:2] == '[[') and (txt[-2:] == ']]'):                    
    #                 groupNo = int(item.text(0).replace('[[', '').replace(']]', '').replace('G', ''))
    #                 group = BoundingBoxGroup.groups[self.parent.scene][groupNo]

    #                 menu = QtWidgets.QMenu()

    #                 collateTextAction = QtWidgets.QAction('Collate', self.parent)
    #                 collateTextAction.setStatusTip('Collate text')
    #                 collateTextAction.triggered.connect(self.collateText)

    #                 menu.addAction(collateTextAction)
    #                 menu.exec_(event.screenPos())

    @QtCore.Slot()
    def onCurrentItemChange(self, current, previous):
        if current:
            currText = current.text(0)

            flagged = False

            if current.parent():
                group = BoundingBoxGroup.groups[self.parent.scene][int(current.parent().text(0).replace('[[', '').replace(']]', '').replace('G', ''))]
                bbox = group.items[current.parent().indexOfChild(current)]
                # self.parent.simpleText.setHtml(f"<span style='background-color:white;color:black;'>{currText}</span>")
                # self.parent.bboxSettings.bbText.setText(currText)
                bbox.updateContent(currText)
                bbox.updateFill()
                if bbox.group:
                    bbox.group.updateShape()

                flagged = bbox.flagged
            elif currText[:2] != '[[' and currText[-2:] != ']]':
                bbType, bbox = self.getBBObjectFromItem(current)

                if bbox:
                    if bbType == 'bbox':
                        bbox:BoundingBox = bbox

                        bbox.updateContent(currText)
                        bbox.updateFill()
                        if bbox.group:
                            bbox.group.updateShape()

                        flagged = bbox.flagged

            current.setBackground(0, self.textBackgroundColor(currText, flagged))




class BoundingBoxSettings(QtWidgets.QDockWidget):
    def __init__(self, parent):
        super(BoundingBoxSettings, self).__init__(parent)

        self.parent = parent

        self.bbTree = BoundingBoxTree(self.parent)

        self.fileName = os.path.split(self.parent.imagePath)[-1]

        self.setWindowTitle(f'Bounding Box Overview | {self.fileName}')
        self.bbTree.setHeaderLabel(self.fileName)
        self.bbTree.header().setStretchLastSection(False)
        self.bbTree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self.usButton = QtWidgets.QPushButton('Copy unit separator')
        self.usButton.clicked.connect(self.copyUSEvent)

        self.widget = QtWidgets.QWidget(self)
        self.setWidget(self.widget)

        # self.bbText = QtWidgets.QLineEdit()
        # self.bbText.setStyleSheet( "QLineEdit { font-family: 'Noto Sans Mono', 'Courier', 'Courier New'; }")
        # self.bbText.setPlaceholderText('BBox Text')

        self.layout = QtWidgets.QVBoxLayout()
        # self.gridLayout = QtWidgets.QGridLayout()
        # self.layout.addWidget(self.bbText, 0, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.bbTree, 0, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.usButton, 0, QtCore.Qt.AlignLeft)

        self.layout.addStretch()

        self.widget.setLayout(self.layout)
        # self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        # self.widget.setWindowOpacity(0.5)
        # self.setWindowOpacity(0.5)
        
        # self.layout.addLayout(self.gridLayout)

        self.adjustSize()

        # self.bbText.textChanged.connect(self.onTextChange)
        # self.bbTree.currentItemChanged.connect(self.onItemChange)

    # @QtCore.Slot()
    # def onTextChange(self, txt):
    #     if not self.parent.clickChanged:
    #         rc = self.parent

    #         if rc.fontGeom:
    #             ar = rc.fontGeom.getTextAspectRatio(txt)*rc.lengthBias
    #         else:
    #             ar = rc.charAspectRatio*len(txt)*rc.lengthBias

    #         selectedItems = rc.scene.selectedItems()
    #         for item in rc.scene.items():
    #             if hasattr(item, 'isBbox'):
    #                 if item in selectedItems:
    #                     item.updateContent(txt)
    #                     item.updateFill()
    #                     if item.treeItem:
    #                         item.treeItem.setText(0, txt)
    #                         self.bbTree.scrollToItem(item.treeItem)
    #                         self.bbTree.setCurrentItem(item.treeItem)
    #     else:
    #         self.parent.clickChanged = False

    @QtCore.Slot()
    def copyUSEvent(self):
        app.clipboard().setText('␟')

# class Corners(IntEnum):
#     TopLeft = 0
#     BottomLeft = 1
#     BottomRight = 2
#     TopRight = 3

# class BoundingBoxHandle(QtWidgets.QGraphicsRectItem, QtCore.QObject):
#     corners = [
#         [0, 0],
#         [0,-1],
#         [1,-1],
#         [1, 0]
#     ]

#     resizeSignal = QtCore.Signal(QtCore.QPointF)

#     def __init__(self, s=10, corner=Corners.BottomRight, parent=None):
#         super(BoundingBoxHandle, self).__init__(0,0, s,s)
#         self.parent = parent
#         self.s = s

#         self.setCorner(corner)
        
#         self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
#         self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable)
#         self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

#     def setCorner(self, corner):
#         self.corner = corner
#         delta = QtCore.QPointF(self.s/2, self.s/2)

#         if corner == Corners.TopLeft:
#             self.setPos(self.parent.rect().topLeft() - delta)
#         elif corner == Corners.BottomLeft:
#             self.setPos(self.parent.rect().bottomLeft() - delta)
#         elif corner == Corners.TopRight:
#             self.setPos(self.parent.rect().topRight() - delta)
#         else:
#             self.setPos(self.parent.rect().bottomRight() - delta)

#     def itemChange(self, change, value):
#         if change == QtWidgets.QGraphicsItem.ItemPositionChange:
#             if self.isSelected():
#                 self.resizeSignal.emit(value - self.pos())

#         return value

class TranslationDialog(QtWidgets.QDockWidget):
    def __init__(self, parent):
        super(TranslationDialog, self).__init__(parent)

        self.parent = parent

        self.fileName = os.path.split(self.parent.imagePath)[-1]
        self.setWindowTitle(f'Translation | {self.fileName}')

        self.widget = QtWidgets.QWidget(self)
        self.setWidget(self.widget)

        self.collationTextEdit = QtWidgets.QTextEdit()

        self.fetchCollationButton = QtWidgets.QPushButton('Fetch collation')
        self.translateButton = QtWidgets.QPushButton('Translate')

        self.translationTextEdit = QtWidgets.QTextEdit()

        self.layout = QtWidgets.QVBoxLayout()
        self.gridLayout = QtWidgets.QGridLayout()

        self.widget.setLayout(self.layout)
        self.layout.addWidget(self.collationTextEdit, 0, QtCore.Qt.AlignCenter)

        self.gridLayout.addWidget(self.fetchCollationButton, 0, 0)
        self.gridLayout.addWidget(self.translateButton, 0, 1)
        self.layout.addLayout(self.gridLayout)

        self.layout.addWidget(self.translationTextEdit, 0, QtCore.Qt.AlignCenter)

        self.layout.addStretch()

        self.fetchCollationButton.clicked.connect(self.fetchCollation)
        self.translateButton.clicked.connect(self.translate)

        self.fetchCollation()

        self.adjustSize()

    @QtCore.Slot()
    def fetchCollation(self):
        collation = []
        for groupNo in sorted(list(BoundingBoxGroup.groups[self.parent.scene].keys())):
            if BoundingBoxGroup.groups[self.parent.scene][groupNo]:
                lines = []
                for bbox in BoundingBoxGroup.groups[self.parent.scene][groupNo].items:
                    text = bbox.text
                    if text != '␟':
                        lines.append(text)

                line = self.parent.retcomconfig.collationString.join(lines)
                collation.append(line)

        self.collationTextEdit.setText('\n\n'.join(collation))

    @QtCore.Slot()
    def translate(self):
        sourceText = self.collationTextEdit.toPlainText()
        # print(sourceText)
        destText = self.parent.translator.translate(sourceText, detailed=True, target=self.parent.retcomconfig.translationLanguage)

        # print()
        # print(destText)
        
        self.translationTextEdit.setText(destText['resp'])

class InfoDialog(QtWidgets.QDockWidget):
    def __init__(self, parent):
        super(InfoDialog, self).__init__(parent)

        self.parent = parent

        self.fileName = os.path.split(self.parent.imagePath)[-1]
        self.setWindowTitle(f'Info | {self.fileName}')

        self.widget = QtWidgets.QWidget(self)
        self.setWidget(self.widget)

        self.avgWidthText = QtWidgets.QLabel(self)
        self.avgHeightText = QtWidgets.QLabel(self)

        self.refreshButton = QtWidgets.QPushButton('Refresh')


        self.layout = QtWidgets.QVBoxLayout()
        self.gridLayout = QtWidgets.QGridLayout()

        self.widget.setLayout(self.layout)
        self.layout.addWidget(self.avgWidthText, 0, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.avgHeightText, 0, QtCore.Qt.AlignLeft)

        self.gridLayout.addWidget(self.refreshButton, 0, 0)
        # self.gridLayout.addWidget(self.translateButton, 0, 1)
        self.layout.addLayout(self.gridLayout)

        # self.layout.addWidget(self.translationTextEdit, 0, QtCore.Qt.AlignCenter)

        self.layout.addStretch()

        self.refreshButton.clicked.connect(self.refresh)
        # self.translateButton.clicked.connect(self.translate)

        self.refresh()

        self.adjustSize()

    @QtCore.Slot()
    def refresh(self):
        bboxes = self.parent.bboxes
        w = 0
        h = 0

        for bbox in bboxes:
            w += bbox.currentW
            h += bbox.currentH

        l = len(bboxes)
        if l > 0:
            w /= l
            h /= l
        
        self.avgWidthText.setText(f'Avg. width: {int(w)}px')
        self.avgHeightText.setText(f'Avg. height: {int(h)}px')

class BoundingEllipse(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x=0, y=0, w=100, h=100, parent=None):
        super(BoundingEllipse, self).__init__(0,0, w,h)
        self.setPos(x, y)

        self.parent = parent

        self.actualW = w
        self.actualH = h

        self.currentW = w
        self.currentH = h

        self.origX = x
        self.origY = y
        self.origW = w
        self.origH = h

        self.sceneX = x
        self.sceneY = y

        self.y0 = 0
        self.margin = 5

        self.origText = None
        self.text = None
        self._fontSize = 25
        self.displayTextItem = QtWidgets.QGraphicsTextItem('', self)
        # self.displayTextItem.setPen
        self.displayTextItem.setPos(self.sceneX, self.sceneY)
        self.displayTextItem.setTextWidth(self.boundingRect().width())
        self.displayText = ''

        self.font = QtGui.QFont('Wild Words')
        self.fontSize = 25

        self.isBell = True
        self.flagged = False

        self.parent.scene.addItem(self.displayTextItem)

        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

        self.alignContents()

        # self.handle = BoundingBoxHandle(parent=self)
        # self.handle.resizeSignal.connect(self.resize)
        # self.parent.scene.addItem(self.handle)

    @property
    def fontSize(self):
        return self._fontSize

    @fontSize.setter
    def fontSize(self, size):
        self._fontSize = abs(size)
        self.font.setPixelSize(self._fontSize)
        self.displayTextItem.setFont(self.font)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, txt):
        self._text = txt

        if txt == '␟':
            self.setZValue(2)
        else:
            self.setZValue(-1)

    @property
    def displayText(self):
        return self._displayText

    @displayText.setter
    def displayText(self, txt):
        self._displayText = txt
        txtFormatted = self.displayText.replace('\n', '<br>')
        self.displayTextItem.setHtml(f'<p style="margin: {self.margin}px; text-align: center; -webkit-text-stroke: 3px #fff; -webkit-text-fill-color: #000;">{txtFormatted}</p>')


    @property
    def aspectRatio(self):
        # h = self.origH
        h = self.actualH

        # w = self.origW
        w = self.actualW

        if self.parent.verticalText:
            return self.origH/self.origW
        else:
            return self.origW/self.origH

    def removeSelected(self):
        self.parent.scene.removeItem(self)

        selectedItems = self.parent.scene.selectedItems()
        if len(selectedItems) > 1:
            for item in self.parent.scene.items():
                if hasattr(item, 'isBbox'):
                    if item in selectedItems:
                        self.parent.scene.removeItem(item)
                        self.parent.bboxes.remove(item)
                        if item.group:
                            group = item.group
                            item.group.remove(item)
                            group.updateShape()

    def restoreSelected(self):
        self.setPos(self.origX, self.origY)
        if self.group:
            self.group.updateShape()

        selectedItems = self.parent.scene.selectedItems()
        if len(selectedItems) > 1:
            for item in self.parent.scene.items():
                if hasattr(item, 'isBbox'):
                    if item in selectedItems:
                        item.setPos(item.origX, item.origY)
                        item.updateContent(item.origText)
                        item.updateFill()

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()

        changeTextAction = QtWidgets.QAction(f'Change text', self.parent)
        changeTextAction.setStatusTip('Change text')
        changeTextAction.triggered.connect(self.changeTextEvent)

        changeFontSizeAction = QtWidgets.QAction(f'Change font size', self.parent)
        changeFontSizeAction.setStatusTip('Change font size')
        changeFontSizeAction.triggered.connect(self.changeFontSizeEvent)

        changeFontFamilyAction = QtWidgets.QAction(f'Change font family', self.parent)
        changeFontFamilyAction.setStatusTip('Change font family')
        changeFontFamilyAction.triggered.connect(self.changeFontFamilyEvent)

        capitalizeAction = QtWidgets.QAction(f'Capitalize text', self.parent)
        capitalizeAction.setStatusTip('Capitalize text')
        capitalizeAction.triggered.connect(self.capitalizeEvent)

        menu.addAction(changeTextAction)
        menu.addAction(changeFontSizeAction)
        menu.addAction(changeFontFamilyAction)
        menu.addAction(capitalizeAction)
        menu.exec_(event.screenPos())

    def changeTextEvent(self):
        txt, resp = QtWidgets.QInputDialog.getMultiLineText(self.parent, 'Textbox text', 'Text:', self.displayText)
        if txt:
            self.displayText = txt
            self.alignContents()

    def changeFontSizeEvent(self):
        size, resp = QtWidgets.QInputDialog.getInt(self.parent, 'Font size', 'Font size in px:', self.fontSize)
        if size:
            self.fontSize = abs(size)
            self.font.setPixelSize(self.fontSize)
            self.displayTextItem.setFont(self.font)
            self.alignContents()

    def changeFontFamilyEvent(self):
        family, resp = QtWidgets.QInputDialog.getText(self.parent, 'Font family', 'Font family:', text=self.font.family())
        if family:
            self.font.setFamily(family)
            self.displayTextItem.setFont(self.font)
            self.alignContents()

    def capitalizeEvent(self):
        self.displayText = self.displayText.upper()
        self.alignContents()

    def mousePressEvent(self, event):
        self.parent.clickChanged = True
        
        if event.button() == QtCore.Qt.LeftButton:
            pass
            # self.parent.simpleText.setHtml(f"<span style='background-color:white;color:black;'>{self.text}</span>")
            # self.parent.bboxSettings.bbText.setText(self.text)
            # if self.treeItem:
            #     self.parent.bboxSettings.bbTree.scrollToItem(self.treeItem)
            #     self.parent.bboxSettings.bbTree.setCurrentItem(self.treeItem)
            # self.parent.simpleText.setText(self.text)
            # print(f"{self.text}; {event.pos().x(), event.pos().y()}")
        # elif event.button() == QtCore.Qt.RightButton:
        #     self.removeSelected()
        elif event.button() == QtCore.Qt.MiddleButton:
            self.restoreSelected()
            # self.setRect(self.origX, self.origX, self.origW, self.origH)
            # print(self.origX, self.origY)
            # print(self.pos())
            # print(self.scenePos())

    def updateContent(self, txt):
        if self.parent.retcomconfig.fullWidth:
            txt = half2fullWidth(txt)
        else:
            txt = full2halfWidth(txt)

        if txt != '␟':
            rc = self.parent

            if rc.fontGeom:
                ar = rc.fontGeom.getTextAspectRatio(txt)*rc.lengthBias
            else:
                ar = rc.charAspectRatio*len(txt)*rc.lengthBias

            self.text = txt

            if rc.verticalText:
                w = self.rect().width()
                self.resize(w, ar*w)
            else:
                h = self.rect().height()
                self.resize(ar*h, h)
        else:
            self.text = txt

    def updateFill(self):
        if self.isSelected():
            self.setBrush(self.parent.retcomconfig.selectedBoxBrush)
        else:
            if self.text == '␟':
                self.setBrush(self.parent.retcomconfig.textBoxBrush)
            elif self.flagged: 
                self.setBrush(self.parent.retcomconfig.flaggedBoxBrush)
            else:
                self.setBrush(self.parent.retcomconfig.boundingBoxBrush)


    def resize(self, w, h):
        self.currentW = w
        self.currentH = h

        self.prepareGeometryChange()
        self.setRect(self.rect().adjusted(0,0, w-self.rect().width(),h-self.rect().height()))
        self.displayTextItem.setTextWidth(self.boundingRect().width())
        self.alignContents()
        self.update()

    def alignContents(self):
        topLeft = self.sceneBoundingRect().topLeft()
        self.sceneX = topLeft.x()
        self.sceneY = topLeft.y()
        self.displayTextItem.setPos(self.sceneX, self.sceneY + self.y0 + round(self.currentH - self.displayTextItem.sceneBoundingRect().height())/2)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            self.alignContents()
            # print('item pos change')
            # if self.group:
            #     # print('updating shape...')
            #     self.group.updateShape()

        return value

    def disband(self):
        self.parent.scene.removeItem(self.displayTextItem)

def runTesseract(path, tessdata, lang='jpn_vert', relPath=None):
    if relPath:
        head, tail = os.path.split(path)
        boxPathDir = os.path.normpath(os.path.join(head, relPath))
        boxPath = os.path.normpath(os.path.join(boxPathDir, tail))

        if not os.path.exists(boxPathDir):
            os.makedirs(boxPathDir)
    else:
        boxPath = path

    path = os.path.normpath(path)

    if not os.path.exists(boxPath + '.py.box'):
        proc = subprocess.Popen(' '.join(['tesseract', '-l', lang, '"'+path+'"', '"'+boxPath + '.py"', '--psm', '12', '--tessdata-dir', '"'+tessdata+'"', 'lstmbox']), stdout=subprocess.PIPE, shell=True)
        output, err = proc.communicate()
        proc.wait()

    return boxPath + '.py.box'

def runTesseractScan(path, tessdata, lang='jpn_vert'):
    path = os.path.normpath(path)
    proc = subprocess.Popen(' '.join(['tesseract', '-l', lang, '"'+path+'"', 'stdout', '--tessdata-dir', '"'+tessdata+'"']), stdout=subprocess.PIPE, shell=True)
    output, err = proc.communicate()
    proc.wait()

    return output

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    translator = Translator(['translate.google.com'])

    retcomconfig = RetComConfig()
    QtGui.QFontDatabase.addApplicationFont(os.path.normpath(os.path.join(retcomconfig.fontPath, 'NotoSansMono-Regular.ttf')))

    RetCom.openRetCom(retcomconfig, translator)

    sys.exit(app.exec_())

