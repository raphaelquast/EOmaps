from eomaps import Maps
from scipy.ndimage import gaussian_filter
from matplotlib.colors import to_rgb
import numpy as np


def scale_to_range(a, mi, ma):
    """
    Scale values of an array between 2 values.

    Parameters
    ----------
    a : array-like
        The values that should be re-scaled.
    mi, ma: float
        The minimum and maximum value to which the array "a" should be scaled.

    Returns
    -------
    a : array-like
        The values scaled to the range [mi, ma]

    """
    amax = np.max(a)
    if amax == 0:
        return a
    a += -(np.min(a))
    a /= amax / (ma - mi)
    a += mi
    return a


# Define an agg-filter function to get a blurry map boundary
def gaussian_blur(sigma=1, blurrcolor="r", truncate=4, radius=None, **kwargs):
    """
    An agg-filter function to apply a 'gaussian-blurr' to an artist.

    All kwargs are passed to `scipy.ndimage.gaussian_filter`.

    Parameters
    ----------
    sigma : int, optional
        The standard-deviation of the gaussian kernel.
        The default is 1.
    blurrcolor : str or rgb-tuple, optional
        The color to use as background-color for the artist when applying
        the gaussian-filter. The default is "r".
    truncate : int, optional
        Truncate the filter at this many standard deviations.
        The default is 4.
    radius : int, or sequence of int, optional
        The radius of the gaussian kernel. If provided, truncate is ignored
        and the size of the kernel is 2*radius + 1.
        The default is None.
    kwargs :
        Additional kwargs are passed to `scipy.ndimage.gaussian_filter`.

    Returns
    -------
    callable
        A agg-filter-function for matpltolib artists.

    """

    def agg_filter(im, dpi):
        # make sure filter properties scale with dpi changes
        s, r = int(sigma / 72 * dpi), int(radius / 72 * dpi) if radius else None
        # pad the image to avoid artefacts on the boundary
        pad = (2 * r + 1) if r else 2 * (s * truncate)
        padded_src = np.pad(im, [(pad, pad), (pad, pad), (0, 0)], "constant")
        # set all transparent image parts to the blurrcolor
        padded_src[..., :3][padded_src[..., 3] == 0] = to_rgb(blurrcolor)
        # apply gaussian filter to all channels
        padded_src = gaussian_filter(padded_src, (s, s, 0), radius=r, **kwargs)
        # maintain the alpha value-range after filtering
        mi, ma = (getattr(im[..., 3], f)() for f in ("min", "max"))
        if mi != ma:
            padded_src[..., 3] = scale_to_range(padded_src[..., 3], mi, ma)
        return padded_src, -pad, -pad

    return agg_filter


# %%
countries = ["Austria"]

# Create a new map with a black figure background
m = Maps(3857, figsize=(8, 4.5), facecolor="k")
# Make the map frame black and let the boarder fade into black
m.set_frame(rounded=1, lw=1, ec="k", fc="k", agg_filter=gaussian_blur(10, "k"))

# Get a geo-data frame with the NaturalEarth county-borders
gdf_all_countries = m.add_feature.cultural.admin_0_countries.get_gdf(scale=50)
gdf_other = gdf_all_countries[~gdf_all_countries.NAME.isin(countries)]
gdf_country = gdf_all_countries[gdf_all_countries.NAME.isin(countries)]

# Add blurry white lines for the country-borders
m.add_gdf(gdf_other, fc="none", ec="w", alpha=0.1, agg_filter=gaussian_blur(3, "w"))
m.add_gdf(gdf_other, fc="none", lw=0.25, ec="w", alpha=0.8)

# Highlight the country
m.add_gdf(
    gdf_country, fc="none", lw=2, ec="w", alpha=0.5, agg_filter=gaussian_blur(5, "w")
)
m.add_gdf(gdf_country, fc="none", lw=0.5, ec="w", alpha=0.8)

# Add features and webmap services
m.add_wms.ESA_WorldCover.add_layer.WORLDCOVER_2021_S2_TCC(alpha=0.5)
m.add_feature.preset.ocean(scale=10, zorder=1)
m.add_text(0.5, 0.95, "Austria / Europe / Earth", c="w", fontsize=15, weight="bold")

# --------------- add a second map for the inset
m2 = m.new_map(crs=m.crs_plot, layer="overlay")
# Make sure the maps share axes limits
m2.join_limits(m)
# Set the map frame to the country-border
m2.set_frame(gdf=gdf_country, lw=1, ec="w", alpha=0.25, set_extent=False)
# Add webmap service
m2.add_wms.ESA_WorldCover.add_layer.WORLDCOVER_2021_S2_TCC()


# Set the map-extent
m.set_extent_to_location("Austria", buffer=0.2)
# Adjust subplots
m.subplots_adjust(top=0.95, bottom=0.05, left=0.05, right=0.95)
m.show_layer("base", "overlay")
m.add_logo()
