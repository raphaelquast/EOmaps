from ..cb_container import CallbackContainer


class CallbackMixin:
    cb = CallbackContainer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initialize accessor for callbacks
        self.cb = CallbackContainer(self)
        self.cb._init_cbs()

        if not hasattr(self.parent, "_execute_callbacks"):
            self.parent._execute_callbacks = True

    @property
    def __lazy_attrs(self):
        # list of attributes that support lazy-evaluation
        return ["cb"]
