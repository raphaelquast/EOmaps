import weakref

from ..cb_container import CallbackContainer


class CallbackMixin:
    cb = CallbackContainer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initialize accessor for callbacks
        self.cb = CallbackContainer(weakref.proxy(self))
        self.cb._init_cbs()

        if not hasattr(self.parent, "_execute_callbacks"):
            self.parent._execute_callbacks = True
