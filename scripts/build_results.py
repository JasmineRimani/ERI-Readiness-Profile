"""Regenerate every result of the public release: capabilities, readiness profiles and policy layer."""
import sys
import _bootstrap  # noqa: F401
from eri.cli import main

if __name__ == '__main__':
    main(['all', *sys.argv[1:]])
