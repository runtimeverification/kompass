from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.__main__ import _arg_parser as kmir_arg_parser
from kmir.__main__ import _parse_args as kmir_parse_args
from kmir.cargo import CargoProject
from kmir.options import KMirOpts, ProveRSOpts, PruneOpts, RunOpts
from kmir.options import ShowOpts as KMirShowOpts
from kmir.options import ViewOpts as KMirViewOpts
from kmir.smir import SMIRInfo
from pyk.cterm.show import CTermShow
from pyk.kast.pretty import PrettyPrinter
from pyk.proof.reachability import APRProof
from pyk.proof.show import APRProofShow
from pyk.proof.tui import APRProofViewer

from .kompass import HASKELL_DEF_DIR, LLVM_DEF_DIR, LLVM_LIB_DIR, Kompass, KompassAPRNodePrinter
from .options import BuildOpts, ProveOpts, ShowOpts, ViewOpts, kompass_parser, mk_kompass_opts

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Sequence
    from typing import Final


_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def _kompass_run(opts: RunOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR) if opts.symbolic else Kompass(LLVM_DEF_DIR)

    if opts.file:
        smir_info = SMIRInfo.from_file(Path(opts.file))
    else:
        cargo = CargoProject(Path.cwd())
        smir_info = cargo.smir_for_project(clean=False)

    result = kompass.run_smir(smir_info, start_symbol=opts.start_symbol, depth=opts.depth)
    print(kompass.kore_to_pretty(result))


def _kompass_prove_rs(opts: ProveRSOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR, bug_report=opts.bug_report)
    proof = kompass.prove_rs(opts)
    print(str(proof.summary))
    if not proof.passed:
        sys.exit(1)


def _kompass_view(opts: KMirViewOpts) -> None:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR)
    proof = APRProof.read_proof_data(opts.proof_dir, opts.id)
    printer = PrettyPrinter(kompass.definition)
    omit_labels = ('<currentBody>',) if opts.omit_current_body else ()
    cterm_show = CTermShow(printer.print, omit_labels=omit_labels)
    opts.full_printer = False
    node_printer = KompassAPRNodePrinter(cterm_show, proof, opts)
    viewer = APRProofViewer(proof, kompass, node_printer=node_printer, cterm_show=cterm_show)
    viewer.run()


def _kompass_show(opts: KMirShowOpts) -> str:
    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR)
    proof = APRProof.read_proof_data(opts.proof_dir, opts.id)
    printer = PrettyPrinter(kompass.definition)
    omit_labels = ('<currentBody>',) if opts.omit_current_body else ()
    cterm_show = CTermShow(printer.print, omit_labels=omit_labels)
    node_printer = KompassAPRNodePrinter(cterm_show, proof, opts)
    shower = APRProofShow(kompass.definition, node_printer=node_printer)
    lines = shower.show(proof)
    return '\n'.join(lines)  # output redirection in caller


def _kompass_prune(opts: PruneOpts) -> None:
    proof = APRProof.read_proof_data(opts.proof_dir, opts.id)
    pruned_nodes = proof.prune(opts.node_id)
    print(f'Pruned nodes: {pruned_nodes}')
    proof.write_proof_data()


def _run_build(opts: BuildOpts) -> None:
    assert isinstance(opts.project_dir, Path)
    cargo = CargoProject(opts.project_dir)

    _LOGGER.info('Rebuilding project with Cargo')
    _ = cargo.smir_for_project(opts.do_clean)


def _run_prove(opts: ProveOpts) -> bool:
    cargo = CargoProject(opts.project_dir)
    target_dir = Path(cargo.metadata['target_directory'])
    smir = target_dir / 'debug' / 'linked.smir.json'

    _LOGGER.debug(f'Running proof for {opts.start_symbol} using file {smir}')

    # check that file exists, rebuild if reload requested
    if opts.reload:
        _ = cargo.smir_for_project(clean=True)
    else:
        assert smir.exists(), f'File {smir} does not exist, please rebuild'

    kompass = Kompass(HASKELL_DEF_DIR, LLVM_LIB_DIR, bug_report=opts.bug_report)

    prove_rs_opts = ProveRSOpts(
        rs_file=smir,
        proof_dir=opts.proof_dir if opts.proof_dir is not None else target_dir / 'proofs',
        bug_report=opts.bug_report,
        max_depth=opts.max_depth,
        max_iterations=opts.max_iterations,
        reload=opts.reload,
        save_smir=False,
        smir=True,
        start_symbol=opts.start_symbol,
    )
    proof = kompass.prove_rs(prove_rs_opts)
    print(str(proof.summary))
    return proof.passed


def _run_view(opts: ViewOpts) -> None:
    cargo = CargoProject(opts.project_dir)
    target_dir = Path(cargo.metadata['target_directory'])
    proof_dir = target_dir / 'proofs' if opts.proof_dir is None else opts.proof_dir

    kmir_view_opts = KMirViewOpts(
        proof_dir=proof_dir,
        id=opts.id,
        full_printer=opts.full_display,
        smir_info=target_dir / 'debug' / 'linked.smir.json',
        omit_current_body=True,
        haskell_target=None,
        llvm_lib_target=None,
    )
    _kompass_view(kmir_view_opts)


def _run_show(opts: ShowOpts) -> None:
    cargo = CargoProject(opts.project_dir)
    target_dir = Path(cargo.metadata['target_directory'])
    proof_dir = target_dir / 'proofs' if opts.proof_dir is None else opts.proof_dir

    kmir_show_opts = KMirShowOpts(
        proof_dir=proof_dir,
        id=opts.id,
        full_printer=opts.full_display,
        smir_info=target_dir / 'debug' / 'linked.smir.json',
        omit_current_body=True,
    )
    output = _kompass_show(kmir_show_opts)
    # redirection to file implemented here
    if opts.output is None:
        print(output)
    else:
        # write to file output
        with open(opts.output, 'w', encoding='utf-8') as f:
            f.write(output)


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
        # handle commands using the kmir parser when prefixed `kmir`
        case 'kmir':
            _LOGGER.warning(f'INFO {args[1]} command handled by kmir parser.\n')
            parser = kmir_arg_parser()
            parser.prog = 'kompass kmir'
            ns, remaining = parser.parse_known_args(args[1:])
            logging.basicConfig(level=_loglevel(ns), format=_LOG_FORMAT)
            opts = kmir_parse_args(ns)
        case _:
            ns = kompass_parser().parse_args(args)
            logging.basicConfig(level=_loglevel(ns), format=_LOG_FORMAT)
            opts = mk_kompass_opts(ns)
    match opts:
        case BuildOpts():
            _run_build(opts)
        case ProveOpts():
            passed = _run_prove(opts)
            if not passed:
                sys.exit(1)
        case ViewOpts():
            _run_view(opts)
        case ShowOpts():
            _run_show(opts)
        # ----- kmir functionality below
        case RunOpts():
            _kompass_run(opts)
        case KMirViewOpts():
            _kompass_view(opts)
        case KMirShowOpts():
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
    sys.setrecursionlimit(10000000)
    kompass(sys.argv[1:])
