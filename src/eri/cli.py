"""Command line interface: ``eri-profile`` or ``python -m eri``."""
import argparse
from pathlib import Path


def main(argv=None):
    """Parse a command, accepting explicit arguments for source-tree wrappers."""
    parser = argparse.ArgumentParser(description="Ecosystem-readiness profiles for early-phase ECLSS design (no scalar score).")
    sub = parser.add_subparsers(dest="command", required=True)
    profile = sub.add_parser('profile', help='Generate the readiness profiles, roadmap and schedule-stress figures')
    profile.add_argument('--out', type=Path, default=Path('outputs/readiness_profile'))
    capabilities = sub.add_parser('capabilities', help='Assess capability work, supply routes, blockers and stress drivers')
    capabilities.add_argument('--out', type=Path, default=Path('outputs/capabilities'))
    policy = sub.add_parser('policy', help='Read the readiness profile as programme and funding decisions (policy layer)')
    policy.add_argument('--out', type=Path, default=Path('outputs/policy_layer'))
    everything = sub.add_parser('all', help='Run capabilities, profile and policy layer into one output folder')
    everything.add_argument('--out', type=Path, default=Path('outputs'))
    sub.add_parser('inputs', help='Show the active input location and the engineering source')
    args = parser.parse_args(argv)
    if args.command in ('capabilities', 'all'):
        from eri.capability_publication import export
        print(export(args.out / 'capabilities' if args.command == 'all' else args.out).resolve())
    if args.command in ('profile', 'all'):
        from eri.readiness_profile import export
        print(export(args.out / 'readiness_profile' if args.command == 'all' else args.out).resolve())
    if args.command in ('policy', 'all'):
        from eri.policy_layer import export
        out = args.out / 'policy_layer' if args.command == 'all' else args.out
        export(out)
        print(Path(out).resolve())
    if args.command == 'inputs':
        from eri import engineering
        from eri.io import DATA
        _, _, meta = engineering.snapshot_tables()
        print(f"Inputs: {DATA}\nEngineering source: {engineering.source()} "
              f"(snapshot generated {meta['generated']})\nStatus: analyst scenarios; no calibrated probabilities")
