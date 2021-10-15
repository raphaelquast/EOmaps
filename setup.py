# -*- coding: UTF-8 -*-

"""
This file is part of EOmaps.
For COPYING and LICENSE details, please refer to the LICENSE file
"""
from setuptools import setup, find_packages

version = "0.1.7"

setup(
    name="EOmaps",
    version=version,
    description="A general-purpose library to generate interactive maps of geographical datasets.",
    packages=find_packages(),
    package_dir={"eomaps": "eomaps"},
    # include_package_data=True,
    author="Raphael Quast",
    author_email="raphael.quast@geo.tuwien.ac.at",
    maintainer="Raphael Quast",
    maintainer_email="raphael.quast@geo.tuwien.ac.at",
    license="GNU General Public License v3 or later (GPLv3+)",
    url="https://github.com/raphaelquast/maps",
    long_description=(
        "A python module to quickly generate interactive "
        + "maps of geographical datasets."
    ),
    install_requires=[
        "numpy",
        "pandas",
        "geopandas",
        "matplotlib>=3.0",
        "cartopy>=0.20.0",
        "descartes",
        "mapclassify",
        "pyproj",
        "pyepsg",
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
)
