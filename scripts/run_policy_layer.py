"""Read the readiness profile as programme and funding decisions (policy layer)."""
import sys
import _bootstrap  # noqa: F401
from eri.cli import main

if __name__ == '__main__':
    main(['policy', *sys.argv[1:]])
