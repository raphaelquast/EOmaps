from matplotlib.transforms import Bbox
from types import SimpleNamespace
import numpy as np
from cartopy.mpl.geoaxes import GeoAxes


class LazyZoomMixin:
    _zoom_scroll_scale_fine = 10
    _zoom_scroll_scale_coarse = 50
    _zoom_lazy_activator_key = " "

    def _connect_zoom_events(self):
        """
        Connect events for lazy-zoom and zoom via scroll-wheel

        Returns
        -------
        cid_scroll, cid_keypress, cid_release: matplotlib callback IDs

        """
        cid_scroll = self.f.canvas.mpl_connect(
            "scroll_event", self._zoom_mousewheel_move
        )
        cid_keypress = self.f.canvas.mpl_connect(
            "key_press_event", self._activate_lazy_zoom
        )
        cid_release = self.f.canvas.mpl_connect(
            "key_release_event", self._deactivate_lazy_zoom
        )

        return (cid_scroll, cid_keypress, cid_release)

    @staticmethod
    def _add_lazy_zoom_axes_image(ax):
        """
        Create a static image of the axes that is used for lazy-zooming.

        Parameters
        ----------
        ax : matplotlib.Axes
            The axes to use.

        Returns
        -------
        axi : matplotlib.Axes
            The axes object containing the image used for zooming.

        """
        x0, y0, x1, y1 = ax.bbox.bounds
        (x0, y0), (x1, y1) = np.floor([x0, y0]), np.ceil([x1, y1])
        bbox = Bbox.from_bounds(x0, y0, x1, y1)
        ax._eomaps_img_buffer = ax.figure.canvas.copy_from_bbox(bbox)

        axi = ax.figure.add_axes(ax.get_position())
        axi.imshow(ax._eomaps_img_buffer, zorder=-100, alpha=0.75)
        # axi.get_xaxis().set_visible(False)
        # axi.get_yaxis().set_visible(False)
        axi.tick_params(
            which="both",
            axis="both",
            left=False,
            right=False,
            bottom=False,
            top=False,
            labelleft=False,
            labelright=False,
            labelbottom=False,
            labeltop=False,
        )
        for _, s in axi.spines.items():
            s.set_linewidth(2)
            s.set_edgecolor("r")

        axi.name = "eomaps_ax_image"
        axi.eomaps_parent_ax = ax

        axi.set_forward_navigation_events(True)
        axi.set_zorder(-9999)

        return axi

    @staticmethod
    def _check_auto_repeat_key(event):
        """
        Check if a keypress event is triggered by auto-repeat.
        (e.g. non-modifier keys tend to re-trigger automatically)

        Parameters
        ----------
        event : matplotlib.KeyPressEvent
            The matpltolib event to check .

        Returns
        -------
        bool: True if event is triggered by auto-repeat, else False

        """
        # check if keypress event is triggered by auto-repeat
        try:
            return event.guiEvent.isAutoRepeat()
        except Exception:
            return False

    def _zoom_mousewheel_move(self, event):
        """A callback to support zooming with the mouse-wheel."""
        ax = event.inaxes

        if not ax:
            return

        if event.key and "shift" in event.key:
            scale = self._zoom_scroll_scale_coarse
        else:
            scale = self._zoom_scroll_scale_fine

        axes = [ax]
        if hasattr(ax, "_temp_zoom_ax"):
            axes.append(ax._temp_zoom_ax)

        for axi in axes:
            axi._pan_start = SimpleNamespace(
                lim=axi.viewLim.frozen(),
                trans=axi.transData.frozen(),
                trans_inverse=axi.transData.inverted().frozen(),
                bbox=axi.bbox.frozen(),
                x=event.x,
                y=event.y,
            )

            if event.button == "up":
                axi.drag_pan(3, event.key, event.x + scale, event.y + scale)
            else:
                axi.drag_pan(3, event.key, event.x - scale, event.y - scale)

        self.redraw()

    def _activate_lazy_zoom(self, event):
        """A callback to activate lazy-zooming."""

        # ignore auto-repeat events to support ordinary keys as modifiers
        if self._check_auto_repeat_key(event):
            return

        if event.key == self._zoom_lazy_activator_key:
            for ax in self.f.axes:
                if not isinstance(ax, GeoAxes):
                    continue

                ax._temp_zoom_ax = self._add_lazy_zoom_axes_image(ax)

            self.BM._disable_draw = True
            self.BM._disable_update = True
            self.f.canvas.draw_idle()

    def _deactivate_lazy_zoom(self, event):
        """A callback to de-activate lazy-zooming."""

        # ignore auto-repeat events to support ordinary keys as modifiers
        if self._check_auto_repeat_key(event):
            return

        for ax in self.f.axes:
            if hasattr(ax, "_temp_zoom_ax"):
                try:
                    ax._temp_zoom_ax.remove()
                    del ax._temp_zoom_ax
                except Exception:
                    continue

        self.BM._disable_draw = False
        self.BM._disable_update = False
        self.redraw()
