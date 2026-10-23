#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="geo-academic-reader",
    version="0.0.1-pre",
    packages=find_packages(),
    py_modules=["doctor"],
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "pypdf>=3.9.0",
        "websockets>=11.0",
    ],
    entry_points={
        "console_scripts": [
            "geo-reader=scripts.run_pipeline:main",
            "geo-doctor=doctor:main",
        ],
    },
)
