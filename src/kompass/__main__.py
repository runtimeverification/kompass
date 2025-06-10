from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.__main__ import _arg_parser as kmir_arg_parser
from kmir.__main__ import _parse_args as kmir_parse_args
from kmir.cargo import CargoProject
from kmir.options import KMirOpts, ProveRawOpts, ProveRSOpts, PruneOpts, RunOpts, ShowOpts, ViewOpts
from kmir.smir import SMIRInfo
from pyk.cli.args import KCLIArgs
from pyk.cterm.show import CTermShow
from pyk.kast.pretty import PrettyPrinter
from pyk.proof.reachability import APRProof, APRProver
from pyk.proof.show import APRProofShow
from pyk.proof.tui import APRProofViewer

from kompass.kompass import HASKELL_DEF_DIR, LLVM_DEF_DIR, LLVM_LIB_DIR, Kompass, KompassAPRNodePrinter

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Sequence
    from typing import Final


_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def _kompass_run(opts: RunOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR) if opts.haskell_backend else Kompass(LLVM_DEF_DIR)

    if opts.file:
        smir_info = SMIRInfo.from_file(Path(opts.file))
    else:
        cargo = CargoProject(Path.cwd())
        # target = opts.bin if opts.bin else cargo.default_target
        smir_info = cargo.smir_for_project(clean=False)

    result = kompass.run_smir(smir_info, start_symbol=opts.start_symbol, depth=opts.depth)
    print(kompass.kore_to_pretty(result))


def _kompass_prove_rs(opts: ProveRSOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR, bug_report=opts.bug_report)
    proof = kompass.prove_rs(opts)
    print(str(proof.summary))
    if not proof.passed:
        sys.exit(1)


def _kompass_prove_raw(opts: ProveRawOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR, bug_report=opts.bug_report)
    claim_index = kompass.get_claim_index(opts.spec_file)
    labels = claim_index.labels(include=opts.include_labels, exclude=opts.exclude_labels)
    for label in labels:
        print(f'Proving {label}')
        claim = claim_index[label]
        if not opts.reload and opts.proof_dir is not None and APRProof.proof_data_exists(label, opts.proof_dir):
            _LOGGER.info(f'Reading proof from disc: {opts.proof_dir}, {label}')
            proof = APRProof.read_proof_data(opts.proof_dir, label)
        else:
            _LOGGER.info(f'Constructing initial proof: {label}')
            proof = APRProof.from_claim(kompass.definition, claim, {}, proof_dir=opts.proof_dir)
        with kompass.kcfg_explore(label) as kcfg_explore:
            prover = APRProver(kcfg_explore, execute_depth=opts.max_depth)
            prover.advance_proof(proof, max_iterations=opts.max_iterations)
        summary = proof.summary
        print(f'{summary}')


def _kompass_view(opts: ViewOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR)
    proof = APRProof.read_proof_data(opts.proof_dir, opts.id)
    printer = PrettyPrinter(kompass.definition)
    omit_labels = ('<currentBody>',) if opts.omit_current_body else ()
    cterm_show = CTermShow(printer.print, omit_labels=omit_labels)
    opts.full_printer = False
    node_printer = KompassAPRNodePrinter(cterm_show, proof, opts)
    viewer = APRProofViewer(proof, kompass, node_printer=node_printer, cterm_show=cterm_show)
    viewer.run()


def _kompass_show(opts: ShowOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR)
    proof = APRProof.read_proof_data(opts.proof_dir, opts.id)
    printer = PrettyPrinter(kompass.definition)
    omit_labels = ('<currentBody>',) if opts.omit_current_body else ()
    cterm_show = CTermShow(printer.print, omit_labels=omit_labels)
    node_printer = KompassAPRNodePrinter(cterm_show, proof, opts)
    shower = APRProofShow(kompass.definition, node_printer=node_printer)
    lines = shower.show(proof)
    print('\n'.join(lines))


def _kompass_prune(opts: PruneOpts) -> None:
    proof = APRProof.read_proof_data(opts.proof_dir, opts.id)
    pruned_nodes = proof.prune(opts.node_id)
    print(f'Pruned nodes: {pruned_nodes}')
    proof.write_proof_data()


# TODO this needs to find a better home
@dataclass
class BuildOpts(KMirOpts):
    project_dir: Path
    do_clean: bool

    def __init___(self, project_dir: Path | str, do_clean: bool = False) -> None:
        self.project_dir = project_dir if isinstance(project_dir, Path) else Path(project_dir)
        self.do_clean = do_clean


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

    return parser


def _run_build(opts: BuildOpts) -> None:
    cargo = CargoProject(opts.project_dir)

    _LOGGER.info('Rebuilding project with Cargo')
    _ = cargo.smir_for_project(opts.do_clean)


def kompass(args: Sequence[str]) -> None:
    if len(args) == 0:
        # How to get both help messages?
        kompass_parser().print_help()
        kmir = kmir_arg_parser()
        kmir.prog = 'kompass'
        kmir.print_help()
        exit(1)
    opts: KMirOpts
    match args[0]:
        # handle specific commands using the kmir parser
        case 'run' | 'prove' | 'show' | 'view' | 'prune' | 'prove-rs':
            parser = kmir_arg_parser()
            parser.prog = 'kompass'
            ns, remaining = parser.parse_known_args(args)
            logging.basicConfig(level=_loglevel(ns), format=_LOG_FORMAT)
            opts = kmir_parse_args(ns)
        case _:
            ns = kompass_parser().parse_args(args)
            logging.basicConfig(level=_loglevel(ns), format=_LOG_FORMAT)
            match ns.command:
                case 'build':
                    opts = BuildOpts(ns.project_dir, ns.rebuild)
                case other:
                    raise AssertionError(f'Parser returned command {other}')  # should have been caught
    match opts:
        case BuildOpts():
            _run_build(opts)
        case RunOpts():
            _kompass_run(opts)
        case ProveRawOpts():
            _kompass_prove_raw(opts)
        case ViewOpts():
            _kompass_view(opts)
        case ShowOpts():
            _kompass_show(opts)
        case PruneOpts():
            _kompass_prune(opts)
        case ProveRSOpts():
            _kompass_prove_rs(opts)
        case _:
            raise AssertionError


def _loglevel(args: Namespace) -> int:
    if args.debug:
        return logging.DEBUG
    if args.verbose:
        return logging.INFO
    return logging.WARNING


def main() -> None:
    kompass(sys.argv[1:])
