from fbs_runtime.application_context.PySide2 import ApplicationContext
from PySide2.QtWidgets import QMainWindow
from retcom import *
from checkTess import *

import glob
import sys

if __name__ == '__main__':
    appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext

    translator = Translator(['translate.google.com'])

    retcomconfig = RetComConfig(appctxt.get_resource(os.path.join('config', 'config.json')))
    retcomconfig.tessdataPath = appctxt.get_resource('tessdata')
    retcomconfig.fontPath = appctxt.get_resource(os.path.join(retcomconfig.fontPath))

    fonts = glob.glob(os.path.normpath(os.path.join(retcomconfig.fontPath, '**/*.ttf')), recursive=True) + glob.glob(os.path.normpath(os.path.join(retcomconfig.fontPath, '**/*.otf')), recursive=True)
    for font in fonts:
        QtGui.QFontDatabase.addApplicationFont(appctxt.get_resource(font))

    if not tessExists():
        check = CheckTess(retcomconfig, translator)
        check.show()
    else:
        RetCom.openRetCom(retcomconfig, translator)

    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)