from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.__main__ import _arg_parser, _parse_args
from kmir.cargo import CargoProject
from kmir.options import RunOpts
from kmir.parse.parser import parse_json

from kompass.kompass import HASKELL_DEF_DIR, LLVM_DEF_DIR, Kompass

if TYPE_CHECKING:
    from collections.abc import Sequence


def kompass(args: Sequence[str]) -> None:
    parser = _arg_parser()
    parser.prog = 'kompass'
    ns, remaining = parser.parse_known_args(args)

    opts = _parse_args(ns)
    match opts:
        case RunOpts():
            _kompass_run(opts)
        case _:
            raise AssertionError


def _kompass_run(opts: RunOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR) if opts.haskell_backend else Kompass(LLVM_DEF_DIR)

    smir_file: Path
    if opts.file:
        smir_file = Path(opts.file).resolve()
    else:
        cargo = CargoProject(Path.cwd())
        target = opts.bin if opts.bin else cargo.default_target
        smir_file = cargo.smir_for(target)

    parse_result = parse_json(kompass.definition, smir_file, 'Pgm')
    if parse_result is None:
        print('Parse error!', file=sys.stderr)
        sys.exit(1)
    kompass_kast, _ = parse_result

    result = kompass.run_parsed(kompass_kast, opts.start_symbol, opts.depth)
    print(kompass.kore_to_pretty(result))


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


def main() -> None:
    kompass(sys.argv[1:])
