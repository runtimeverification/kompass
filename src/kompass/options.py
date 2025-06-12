from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.options import KMirOpts
from kmir.options import ProveOpts as KMirProveOpts
from pyk.cli.args import KCLIArgs

if TYPE_CHECKING:
    from argparse import Namespace


# Each command is run in a cargo context, optionally provided or pwd()
@dataclass
class CargoOpts(KMirOpts):
    project_dir: Path


@dataclass
class BuildOpts(CargoOpts):
    do_clean: bool

    def __init___(self, project_dir: Path, do_clean: bool = False) -> None:
        self.project_dir = project_dir.resolve()
        self.do_clean = do_clean


@dataclass
class ProveOpts(KMirProveOpts, CargoOpts):
    start_symbol: str

    def __init__(
        self,
        project_dir: Path,
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


@dataclass
class ProofOpts(CargoOpts):
    proof_dir: Path | None
    id: str


@dataclass
class ProofDisplayOpts(ProofOpts):
    full_display: bool

    def __init__(
        self,
        project_dir: Path,
        proof_dir: Path | None,
        id: str,
        full_display: bool = False,
    ) -> None:
        self.project_dir = project_dir
        self.proof_dir = proof_dir.resolve() if proof_dir is not None else None
        self.id = id
        self.full_display = full_display


@dataclass
class ViewOpts(ProofDisplayOpts): ...


@dataclass
class ShowOpts(ProofDisplayOpts): ...


def kompass_parser() -> ArgumentParser:
    parser = ArgumentParser(prog='kompass')

    project_parser = ArgumentParser(add_help=False)
    project_parser.add_argument(
        '--project-dir', '-C', metavar='DIR', help='Cargo project directory (default: current directory)'
    )

    command_parser = parser.add_subparsers(dest='command', required=True)
    kcli_args = KCLIArgs()

    build_parser = command_parser.add_parser(
        'build', help='build Stable MIR JSON for a cargo project', parents=[kcli_args.logging_args, project_parser]
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
        'prove',
        help='Run a proof for a program or library',
        parents=[kcli_args.logging_args, project_parser, prove_args],
    )
    prove_parser.add_argument(
        '--start-symbol', type=str, metavar='SYMBOL', default='main', help='Symbol name to begin execution from'
    )

    proof_args = ArgumentParser(add_help=False)
    proof_args.add_argument('id', metavar='PROOF_ID', help='The id of the proof to view')
    proof_args.add_argument('--proof-dir', metavar='DIR', help='Proof directory')

    display_args = ArgumentParser(add_help=False)
    display_args.add_argument(
        '--full',
        dest='full_display',
        action='store_true',
        default=False,
        help='Display the full node in output.',
    )

    command_parser.add_parser(
        'view', help='View a saved proof', parents=[kcli_args.logging_args, project_parser, proof_args, display_args]
    )
    command_parser.add_parser(
        'show', help='Show a saved proof', parents=[kcli_args.logging_args, project_parser, proof_args, display_args]
    )

    # only for sake of the help message:
    command_parser.add_parser('kmir', help='Run commands of the underlying `mir-semantics` CLI')

    return parser


def mk_kompass_opts(ns: Namespace) -> KMirOpts:
    match ns.command:
        case 'build':
            dir = Path.cwd() if ns.project_dir is None else Path(ns.project_dir)
            return BuildOpts(dir, ns.rebuild)
        case 'prove':
            dir = Path.cwd() if ns.project_dir is None else Path(ns.project_dir)
            return ProveOpts(
                dir,
                ns.start_symbol,
                ns.proof_dir,
                ns.bug_report,
                ns.max_depth,
                ns.max_iterations,
                ns.reload,
            )
        case 'view':
            project_dir = Path.cwd() if ns.project_dir is None else Path(ns.project_dir)
            proof_dir = Path(ns.proof_dir) if ns.proof_dir is not None else None
            return ViewOpts(
                project_dir,
                proof_dir,
                ns.id,
                ns.full_display,
            )
        case 'show':
            project_dir = Path.cwd() if ns.project_dir is None else Path(ns.project_dir)
            proof_dir = Path(ns.proof_dir) if ns.proof_dir is not None else None
            return ShowOpts(
                project_dir,
                proof_dir,
                ns.id,
                ns.full_display,
            )
        case other:
            raise AssertionError(f'Parser returned command {other}')  # should have been caught
