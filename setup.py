#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="cloudhome",
    version="1.0",
    packages=find_packages(where="cloudhome"),
    entry_points={"console_scripts": ["cloudhome = cloudhome:main"]},
    include_package_data=True,
)
