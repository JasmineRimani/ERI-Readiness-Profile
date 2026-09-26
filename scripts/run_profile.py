"""Generate the paper's ecosystem-readiness profiles."""
import sys
import _bootstrap  # noqa: F401
from eri.cli import main

if __name__ == '__main__':
    main(['profile', *sys.argv[1:]])
