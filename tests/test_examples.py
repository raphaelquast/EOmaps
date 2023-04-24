import unittest
from pathlib import Path

from matplotlib.testing import compare

import numpy as np
from eomaps import Maps

basepath = Path(__file__).parent
img_folder = basepath / "test_images" / "examples"


def compareit(tol=1, **save_kwargs):
    def decorator(f):
        def wrapper(*args, **kwargs):
            test_img = img_folder / (f.__name__ + ".png")
            compare_img = test_img.parent / (
                test_img.stem + "_compare" + test_img.suffix
            )

            m = f(*args, **kwargs)

            # if not test_img.exists():
            #     m.savefig(test_img, **save_kwargs)
            #     print("Image did not yet exist!!")
            #     return

            m.savefig(compare_img, **save_kwargs)
            ret = compare.compare_images(test_img, compare_img, tol, False)

            if ret is not None:
                raise compare.ImageComparisonFailure(ret)

            return ret

        return wrapper

    return decorator


class TestExamples(unittest.TestCase):
    @compareit()
    def test_example1(self):
        np.random.seed(1)

        from example1 import m

        return m

    @compareit()
    def test_example2(self):
        np.random.seed(1)

        from example2 import m

        return m

    @compareit()
    def test_example3(self):
        np.random.seed(1)

        from example3 import m

        return m

    @compareit()
    def test_example4(self):
        from example4 import m

        return m

    @compareit()
    def test_example5(self):
        from example5 import m

        return m

    @compareit(tol=10)
    def test_example6(self):
        # increase tolerance here since we deal with webmaps!
        from example6 import m

        return m

    @compareit()
    def test_example7(self):
        from example7 import m

        return m

    @compareit()
    def test_example8(self):
        from example8 import m

        return m

    @compareit()
    def test_example9(self):
        from example9 import m

        return m

    @compareit()
    def test_example_inset_maps(self):
        from example_inset_maps import m

        return m

    @compareit()
    def test_example_row_col_selector(self):
        from example_row_col_selector import m

        return m

    @compareit()
    def test_example_lines(self):
        from example_lines import m

        return m
