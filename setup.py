#!/usr/bin/env python3

from distutils.core import setup

setup(
    name="workflow-documenter",
    version="0.1.1",
    description="Generate markdown documentation for Github Actions re-usable workflows.",
    author='Mike "Fuzzy" Partin',
    author_email="mike.partin@aplaceformom.com",
    url="https://github.com/fuzzy/workflow-documenter/",
    scripts=["workflow-documenter.py"],
    requires=["pyyaml"],
)
