from eomaps import Maps, MapsGrid
from qtpy.QtCore import QPoint
import matplotlib.pyplot as plt
Maps.config(companion_widget_key="x")

def get_ax_center_pos(m):
    # Note: QT position is measured from the TOP left corner!
    return QPoint(
        int(m.ax.bbox.x0 + m.ax.bbox.width / 2), 
        int(m.f.bbox.height - m.ax.bbox.y0 - m.ax.bbox.height / 2)
        )

def test_open_companion(qtbot):
    mg = MapsGrid()
    qtbot.addWidget(mg.f.canvas)
        
    for m in mg:
        assert m._companion_widget is None, "Widget already created?"
        qtbot.mouseMove(m.f.canvas, get_ax_center_pos(m))
        qtbot.keyPress(m.f.canvas, m._CompanionMixin__companion_widget_key)
        assert m._companion_widget is not None, "Widget not opened properly"
        assert m._companion_widget.isVisible(), "Widget not visible after opening"
        
        qtbot.mouseMove(m.f.canvas, get_ax_center_pos(m))
        qtbot.keyPress(m.f.canvas, m._CompanionMixin__companion_widget_key)
        assert not m._companion_widget.isVisible(), "Widget not properly hidden"
    
    plt.close("all")