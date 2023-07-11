#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="cloudhome",
    version="1.0",
    packages=find_packages(where="src"),
    entry_points={"console_scripts": ["cloudhome=cloudhome.cloudhome:main"]},
    package_dir={"cloudhome": "src/cloudhome"},
    include_package_data=True,
)
