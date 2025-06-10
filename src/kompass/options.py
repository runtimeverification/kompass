from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

from kmir.options import KMirOpts
from kmir.options import ProveOpts as KMirProveOpts
from pyk.cli.args import KCLIArgs

# from typing import TYPE_CHECKING


@dataclass
class BuildOpts(KMirOpts):
    project_dir: Path
    do_clean: bool

    def __init___(self, project_dir: Path, do_clean: bool = False) -> None:
        self.project_dir = project_dir.resolve()
        self.do_clean = do_clean


@dataclass
class ProveOpts(KMirProveOpts):
    project_dir: Path
    start_symbol: str

    def __init__(
        self,
        project_dir: Path | str,
        start_symbol: str = 'main',
        proof_dir: Path | str | None = None,
        bug_report: Path | None = None,
        max_depth: int | None = None,
        max_iterations: int | None = None,
        reload: bool = False,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.start_symbol = start_symbol
        self.proof_dir = Path(proof_dir).resolve() if proof_dir is not None else None
        self.bug_report = bug_report
        self.max_depth = max_depth
        self.max_iterations = max_iterations
        self.reload = reload


def kompass_parser() -> ArgumentParser:
    parser = ArgumentParser(prog='kompass')

    command_parser = parser.add_subparsers(dest='command', required=True)
    kcli_args = KCLIArgs()

    build_parser = command_parser.add_parser(
        'build', help='build Stable MIR JSON for a cargo project', parents=[kcli_args.logging_args]
    )
    build_parser.add_argument(
        '--project-dir', '-C', metavar='DIR', help='Change to given directory before doing anything'
    )
    build_parser.add_argument('--rebuild', action='store_true', help='Run cargo clean before building')

    prove_args = ArgumentParser(add_help=False)
    prove_args.add_argument('--proof-dir', metavar='DIR', help='Proof directory')
    prove_args.add_argument('--bug-report', metavar='PATH', help='path to optional bug report')
    prove_args.add_argument('--max-depth', metavar='DEPTH', type=int, help='max steps to take between nodes in kcfg')
    prove_args.add_argument(
        '--max-iterations', metavar='ITERATIONS', type=int, help='max number of proof iterations to take'
    )
    prove_args.add_argument('--reload', action='store_true', help='Force restarting proof')

    prove_parser = command_parser.add_parser(
        'prove', help='Run a proof for a program or library', parents=[kcli_args.logging_args, prove_args]
    )
    prove_parser.add_argument(
        '--project-dir',
        type=Path,
        metavar='DIR',
        help='Cargo project directory (default: current directory)',
    )
    prove_parser.add_argument(
        '--start-symbol', type=str, metavar='SYMBOL', default='main', help='Symbol name to begin execution from'
    )

    return parser
