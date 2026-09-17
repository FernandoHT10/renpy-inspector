"""Main entry point for running module via `python -m renpy_inspector`."""

import sys

from renpy_inspector.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
