from fbs_runtime.application_context.PySide2 import ApplicationContext
from PySide2.QtWidgets import QMainWindow
from retcom import *
from checkTess import *

import sys

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext

    translator = Translator(['translate.google.com'])

    retcomconfig = RetComConfig(appctxt.get_resource(os.path.join('config', 'config.json')))
    retcomconfig.tessdataPath = appctxt.get_resource('tessdata')
    print(retcomconfig.tessdataPath)
    retcomconfig.fontPath = appctxt.get_resource(os.path.join(retcomconfig.fontPath))
    print(retcomconfig.fontPath)
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'NotoSansMono-Regular.ttf')))
    
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'wildwordsroman.TTF')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'wildwordsitalic.TTF')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'wildwordsbold.TTF')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'wildwordsbolditalic.TTF')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'mangat.ttf')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'mangatb.ttf')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'mangati.ttf')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'Felt Regular.ttf')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'regular', 'augie.ttf')))

    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'sfx', 'another.ttf')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'sfx', 'bigfish.ttf')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'sfx', 'TrashHand.TTF')))
    QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(os.path.join(retcomconfig.fontPath, 'sfx', 'Vnhltfap.ttf')))

    if not tessExists():
        check = CheckTess(retcomconfig, translator)
        check.show()
    else:
        RetCom.openRetCom(retcomconfig, translator)

    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)