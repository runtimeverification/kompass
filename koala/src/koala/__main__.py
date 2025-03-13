from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.__main__ import main as kmir_main

if TYPE_CHECKING:
    from collections.abc import Sequence


def koala(args: Sequence[str]) -> None:
    ns, remaining = _arg_parser().parse_known_args(args)

    match ns.command:
        case 'run' | 'prove':
            kmir_main()
            sys.exit(0)
        case 'build':
            _run_build(remaining)


def _run_build(args: Sequence[str]) -> None:
    stable_mir_path = Path.home() / '.stable-mir-json'
    if not stable_mir_path.is_dir():
        raise FileNotFoundError(f"Stable MIR doesn't appear to be installed. Tried {stable_mir_path}")

    scripts = list(stable_mir_path.glob('*.sh'))

    if len(scripts) == 0:
        raise FileNotFoundError(f"Couldn't find a stable-mir-json script in the install folder: {stable_mir_path}")

    stable_mir_script = scripts[0]
    os.environ['RUSTC'] = str(stable_mir_script)

    os.execvpe('cargo', ['cargo', 'build', *args], os.environ)


def _arg_parser() -> ArgumentParser:
    parser = ArgumentParser(prog=sys.argv[0])

    command_parser = parser.add_subparsers(dest='command', required=True)

    command_parser.add_parser('run', help='Run a stable MIR solana program')
    command_parser.add_parser('prove', help='Run proofs over a stable MIR solana program')
    command_parser.add_parser('build', help='Compile a solana program into stable MIR')

    return parser


def main() -> None:
    koala(sys.argv[1:])
