from textwrap import dedent, indent, fill
from warnings import warn


class data_specs(object):
    def __init__(
        self,
        m,
        data=None,
        xcoord=None,
        ycoord=None,
        crs=None,
        parameter=None,
    ):
        self._m = m
        self._data = None
        self._xcoord = None
        self._ycoord = None
        self._crs = None
        self._parameter = None

    def __repr__(self):
        txt = f"""\
              ## parameter = {self.parameter}
              ## coordinates = ({self.xcoord}, {self.ycoord})
              ## crs: {indent(fill(self.crs.__repr__(), 50),
                              "                       ").strip()}

              ## data:\
              {indent(self.data.__repr__(), "              ")}
              """

        return dedent(txt)

    def __getitem__(self, key):
        assert key in self.keys(), f"{key} is not a valid data-specs key!"
        return getattr(self, key)

    def __setitem__(self, key, val):
        assert key in self.keys(), f"{key} is not a valid data-specs key!"
        return setattr(self, key, val)

    def keys(self):
        return ("parameter", "xcoord", "ycoord", "in_crs", "data")

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @property
    def crs(self):
        return self._crs

    @crs.setter
    def crs(self, crs):
        self._crs = crs

    in_crs = crs

    @property
    def xcoord(self):
        return self._xcoord

    @xcoord.setter
    def xcoord(self, xcoord):
        self._xcoord = xcoord

    @property
    def ycoord(self):
        return self._ycoord

    @ycoord.setter
    def ycoord(self, ycoord):
        self._ycoord = ycoord

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter

    @parameter.getter
    def parameter(self):
        if self._parameter is None:
            if (
                self.data is not None
                and self.xcoord is not None
                and self.ycoord is not None
            ):

                try:
                    self.parameter = next(
                        i
                        for i in self.data.keys()
                        if i not in [self.xcoord, self.ycoord]
                    )
                    print(f"Parameter was set to: '{self.parameter}'")

                except Exception:
                    warn(
                        "Parameter-name could not be identified!"
                        + "\nCheck the data-specs!"
                    )
        return self._parameter
