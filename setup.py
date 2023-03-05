# -*- coding: UTF-8 -*-

"""
This file is part of EOmaps.
For COPYING and LICENSE details, please refer to the LICENSE file
"""
from setuptools import setup, find_packages
from pathlib import Path
import re

# add the README as long-description
this_directory = Path(__file__).parent
try:
    long_description = (this_directory / "README.md").read_text()
except Exception:
    long_description = "A library to create interactive maps of geographical datasets."

# get version-number from _version.py
try:
    with open(this_directory / "eomaps" / "_version.py") as file:
        (version,) = re.findall('__version__ = "(.*)"', file.read())
except Exception:
    version = "undefined"

setup(
    name="EOmaps",
    version=version,
    description="A library to create interactive maps of geographical datasets.",
    packages=find_packages(),
    package_dir={"eomaps": "eomaps"},
    package_data={"eomaps": ["logo.png", "NE_features.json", "qtcompanion/icons/*"]},
    # include_package_data=True,
    author="Raphael Quast",
    author_email="raphael.quast@geo.tuwien.ac.at",
    maintainer="Raphael Quast",
    maintainer_email="raphael.quast@geo.tuwien.ac.at",
    license="GNU General Public License v3 or later (GPLv3+)",
    url="https://github.com/raphaelquast/maps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "numpy<1.24",  # check progress of https://github.com/numba/numba/pull/8691
        "scipy",
        "pandas",
        "matplotlib>=3.4",
        "cartopy>=0.20.0",
        "descartes",
        "mapclassify",
        "pyproj",
        "pyepsg",
        "geopandas",
        "owslib",
        "requests",
        "xmltodict",
        "cairosvg",
        "packaging",
    ],
    keywords=["visualization", "plotting", "maps", "geographical data"],
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        # Pick your license as you wish (should match "license" above)
        # ~ 'License :: OSI Approved :: MIT License',
        "Programming Language :: Python :: 3.7",
    ],
    license_files=("LICENSE",),
)
