"""A container class for signals sent to the CompanionWidget"""


from qtpy.QtCore import QObject, Signal


class _SignalContainer(QObject):
    cmapsChanged = Signal()

    clipboardKwargsChanged = Signal()

    dataPlotted = Signal()

    # -------- shape drawer
    drawFinished = Signal()
    drawAborted = Signal()
    drawStarted = Signal(str)

    # -------- annotation editor
    annotationEditorActivated = Signal()
    annotationEditorDeactivated = Signal()
    annotationSelected = Signal()
    annotationEdited = Signal()

    # -------- layout editor
    layoutEditorActivated = Signal()
    layoutEditorDeactivated = Signal()
