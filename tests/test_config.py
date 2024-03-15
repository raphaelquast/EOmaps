import unittest
import matplotlib.pyplot as plt
from eomaps import Maps, _log
from eomaps._blit_manager import BlitManager


class TestConfig(unittest.TestCase):
    def test_config_options(self):
        # reset to defaults
        Maps.config(
            companion_widget_key="x",
            always_on_top=True,
            snapshot_on_update=False,
            use_interactive_mode=True,
            log_level=10,
        )

        m = Maps()
        m.add_feature.preset.coastline()
        m.f.canvas.draw()

        self.assertTrue(m._companion_widget_key == "x")
        self.assertTrue(m._always_on_top is True)
        self.assertTrue(m.BM._snapshot_on_update is False)
        self.assertTrue(m._use_interactive_mode is True)
        self.assertTrue(_log.getEffectiveLevel() == 10)

        # reset to defaults
        Maps.config(
            companion_widget_key="w",
            always_on_top=False,
            snapshot_on_update=True,
            use_interactive_mode=False,
            log_level=30,
        )

        m = Maps()
        m.add_feature.preset.coastline()
        m.f.canvas.draw()

        self.assertTrue(m._companion_widget_key == "w")
        self.assertTrue(m._always_on_top is False)
        self.assertTrue(m.BM._snapshot_on_update is True)
        self.assertTrue(m._use_interactive_mode is False)
        self.assertTrue(_log.getEffectiveLevel() == 30)

        # revert to defaults
        Maps._use_interactive_mode = None
        BlitManager._snapshot_on_update = None

        plt.close("all")
