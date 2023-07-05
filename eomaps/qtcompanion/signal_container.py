"""A container class for signals sent to the CompanionWidget"""


from PyQt5.QtCore import QObject, pyqtSignal


class _SignalContainer(QObject):
    cmapsChanged = pyqtSignal()

    drawFinished = pyqtSignal()
    drawAborted = pyqtSignal()
    drawStarted = pyqtSignal(str)

    clipboardKwargsChanged = pyqtSignal()

    annotationSelected = pyqtSignal()
    annotationEdited = pyqtSignal()

    dataPlotted = pyqtSignal()
