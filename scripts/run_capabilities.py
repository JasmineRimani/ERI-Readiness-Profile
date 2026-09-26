"""Export engineering capability, supplier routes and conditional readiness work."""
import sys
import _bootstrap  # noqa: F401
from eri.cli import main

if __name__ == '__main__':
    main(['capabilities', *sys.argv[1:]])
