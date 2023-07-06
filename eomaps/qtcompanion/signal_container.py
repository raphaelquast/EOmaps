"""A container class for signals sent to the CompanionWidget"""


from PyQt5.QtCore import QObject, pyqtSignal


class _SignalContainer(QObject):
    cmapsChanged = pyqtSignal()

    clipboardKwargsChanged = pyqtSignal()

    dataPlotted = pyqtSignal()

    # -------- shape drawer
    drawFinished = pyqtSignal()
    drawAborted = pyqtSignal()
    drawStarted = pyqtSignal(str)

    # -------- annotation editor
    annotationEditorActivated = pyqtSignal()
    annotationEditorDeactivated = pyqtSignal()
    annotationSelected = pyqtSignal()
    annotationEdited = pyqtSignal()

    # -------- layout editor
    layoutEditorActivated = pyqtSignal()
    layoutEditorDeactivated = pyqtSignal()
