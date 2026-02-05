import logging
import matplotlib.pyplot as plt

# arguments passed to m.savefig when using "ctrl+c" to export figure to clipboard
_clipboard_kwargs = {}

_log = logging.getLogger(__name__)


def _set_clipboard_kwargs(**kwargs):
    # use Maps to make sure InsetMaps do the same thing!
    global _clipboard_kwargs
    _clipboard_kwargs = kwargs


def _get_clipboard_kwargs():
    # use Maps to make sure InsetMaps do the same thing!
    global _clipboard_kwargs
    return _clipboard_kwargs


class ClipboardMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __on_keypress(self, event):
        if event.key == "ctrl+c":
            try:
                self._save_to_clipboard(**self._get_clipboard_kwargs())
            except Exception:
                _log.exception(
                    "EOmaps: Encountered a problem while trying to export the figure "
                    "to the clipboard.",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

    def _get_clipboard_kwargs(self):
        return _get_clipboard_kwargs()

    @staticmethod
    def _set_clipboard_kwargs(**kwargs):
        """
        Set GLOBAL savefig parameters for all Maps objects on export to the clipboard.

        - press "control + c" to export the figure to the clipboard

        All arguments are passed to :meth:`Maps.savefig`

        Useful options are

        - dpi : the dots-per-inch of the figure
        - refetch_wms: re-fetch webmaps with respect to the export-`dpi`
        - bbox_inches: use "tight" to export figure with a tight boundary
        - pad_inches: the size of the boundary if `bbox_inches="tight"`
        - transparent: if `True`, export with a transparent background
        - facecolor: the background color


        Parameters
        ----------
        kwargs :
            Keyword-arguments passed to :meth:`Maps.savefig`.

        Note
        ----
        This function sets the clipboard kwargs for all Maps-objects!

        Exporting to the clipboard only works if `PyQt5` is used as matplotlib backend!
        (the default if `PyQt` is installed)

        See Also
        --------
        Maps.savefig : Save the figure as jpeg, png, etc.

        """
        # use Maps to make sure InsetMaps do the same thing!
        _set_clipboard_kwargs(**kwargs)
        # trigger companion-widget setter for all open figures that contain maps
        for i in plt.get_fignums():
            try:
                m = getattr(plt.figure(i), "_EOmaps_parent", None)
                if m is not None:
                    if m._companion_widget is not None:
                        m._emit_signal("clipboardKwargsChanged")
            except Exception:
                _log.exception("UPS")

    def _save_to_clipboard(self, **kwargs):
        """
        Export the figure to the clipboard.

        Parameters
        ----------
        kwargs :
            Keyword-arguments passed to :py:meth:`Maps.savefig`
        """
        import io
        import mimetypes
        from qtpy.QtCore import QMimeData
        from qtpy.QtWidgets import QApplication
        from qtpy.QtGui import QImage

        # guess the MIME type from the provided file-extension
        fmt = kwargs.get("format", "png")
        mimetype, _ = mimetypes.guess_type(f"dummy.{fmt}")

        message = f"EOmaps: Exporting figure as '{fmt}' to clipboard..."
        _log.info(message)

        # TODO remove dependency on companion widget here
        if getattr(self, "_companion_widget", None) is not None:
            self._companion_widget.window().statusBar().showMessage(message, 2000)

        with io.BytesIO() as buffer:
            self.savefig(buffer, **kwargs)
            data = QMimeData()

            cb = QApplication.clipboard()

            # TODO check why files copied with setMimeData(...) cannot be pasted
            # properly in other apps
            if fmt in ["svg", "svgz", "pdf", "eps"]:
                data.setData(mimetype, buffer.getvalue())
                cb.clear(mode=cb.Clipboard)
                cb.setMimeData(data, mode=cb.Clipboard)
            else:
                cb.setImage(QImage.fromData(buffer.getvalue()))
