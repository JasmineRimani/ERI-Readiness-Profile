"""Provenance helpers shared by every exporter: source discovery and hashing.

Each study writes a ``manifest.json`` with three hash groups so that the review
packager can refuse stale or edited assets:

- ``code_sha256``   every module of the four packages (``source_files``)
- ``input_sha256``  the runtime inputs under ``data/`` (``input_hashes``)
- ``output_sha256`` the files the study wrote, except the manifest itself

The functions below are the single implementation of those groups. Exporters
add their own study-specific keys around them.
"""
from importlib import import_module
from importlib.util import find_spec
import hashlib
import json
from pathlib import Path

PACKAGES = ('sizing', 'tris', 'hycost', 'eri')
INPUT_SUFFIXES = ('.yaml', '.csv', '.json')
MANIFEST = 'manifest.json'


def source_files():
    """Map ``src/<package>/<module>.py`` to its path for the installed or source-tree packages.

    Packages that are not installed (a release without the engineering models)
    are skipped, so the hashes describe exactly the code that ran.
    """
    files = {}
    for name in PACKAGES:
        if find_spec(name) is None:
            continue
        folder = Path(import_module(name).__file__).resolve().parent
        files.update({f'src/{name}/{p.name}': p for p in sorted(folder.glob('*.py'))})
    return files


def sha256(path):
    """Hex digest of a file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes():
    """``code_sha256`` group: one digest per module of the four packages."""
    return {name: sha256(path) for name, path in source_files().items()}


def input_hashes(paths=None, root=None):
    """``input_sha256`` group keyed by path relative to ``data/``.

    Without ``paths`` every YAML/CSV/JSON file under ``data/`` is hashed, in
    sorted order, so that two runs on the same tree produce identical manifests.
    """
    from eri.io import DATA
    root = Path(root or DATA)
    if paths is None:
        paths = [p for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in INPUT_SUFFIXES]
    return {str(Path(p).relative_to(root)): sha256(p) for p in paths}


def output_hashes(folder, recursive=False):
    """``output_sha256`` group: every file the study wrote, excluding the manifest."""
    folder = Path(folder)
    files = folder.rglob('*') if recursive else folder.iterdir()
    return {str(p.relative_to(folder)): sha256(p)
            for p in sorted(files) if p.is_file() and p.relative_to(folder) != Path(MANIFEST)}


def write_manifest(folder, manifest):
    """Serialise a manifest next to the study outputs and return its path."""
    path = Path(folder) / MANIFEST
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    return path
