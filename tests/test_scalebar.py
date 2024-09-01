import pytest
from eomaps import Maps


@pytest.mark.mpl_image_compare()
def test_scalebar_display_rotation():

    m = Maps(2154)
    m.add_feature.preset.coastline()

    scb1 = m.add_scalebar((-6, 43.45))
    scb1.set_rotation(0)

    scb2 = m.add_scalebar((2.5, 46))
    scb2.set_rotation(45)

    scb3 = m.add_scalebar((-7, 51))
    scb3.set_rotation(90)

    return m
