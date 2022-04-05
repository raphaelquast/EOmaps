# -*- coding: UTF-8 -*-

"""
This file is part of EOmaps.
For COPYING and LICENSE details, please refer to the LICENSE file
"""
from setuptools import setup, find_packages
from pathlib import Path

# add the README as long-description
this_directory = Path(__file__).parent
try:
    long_description = (this_directory / "README.md").read_text()
except Exception:
    long_description = "A library to create interactive maps of geographical datasets."

version = "3.4.1"

setup(
    name="EOmaps",
    version=version,
    description="A library to create interactive maps of geographical datasets.",
    packages=find_packages(),
    package_dir={"eomaps": "eomaps"},
    package_data={"eomaps": ["logo.png", "NE_features.json"]},
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
        "numpy",
        "scipy",
        "pandas",
        "matplotlib>=3.0",
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
