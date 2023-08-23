#!/usr/bin/env python
# coding=utf8
from setuptools import setup, find_packages
import os

if os.path.exists('requirements.txt'):
    requirements = [x.strip() for x in open("requirements.txt").readlines()]
else:
    requirements = []

# Create build meta
setup(
    name="qcaudit",
    version="{PYPI_VERSION}",
    author="{CI_COMMIT_AUTHOR}",
    url="{DRONE_REMOTE_URL}",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    description="",
    long_description=open("README.md").read(),
)

