#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="geo-academic-reader",
    version="0.5.1",
    packages=find_packages(include=["scripts", "scripts.*"]),
    py_modules=["doctor"],
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "pypdf>=3.9.0",
        "websockets>=11.0",
    ],
    extras_require={
        "figures": ["pymupdf>=1.23"],
        "dev": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": [
            "geo-reader=scripts.run_pipeline:main",
            "geo-doctor=doctor:main",
        ],
    },
)
