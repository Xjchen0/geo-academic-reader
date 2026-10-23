#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Console-script entry point kept for `geo-reader` compatibility."""

import sys

from .cli import main as cli_main


def main(argv=None):
    return cli_main(argv)


if __name__ == "__main__":
    sys.exit(main())
