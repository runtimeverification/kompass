from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.__main__ import _arg_parser as kmir_arg_parser
from kmir.__main__ import _parse_args as kmir_parse_args
from kmir.cargo import CargoProject
from kmir.options import KMirOpts, ProveRawOpts, ProveRSOpts, PruneOpts, RunOpts
from kmir.options import ShowOpts as KMirShowOpts
from kmir.options import ViewOpts as KMirViewOpts
from kmir.smir import SMIRInfo
from pyk.cterm.show import CTermShow
from pyk.kast.pretty import PrettyPrinter
from pyk.proof.reachability import APRProof, APRProver
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


def _kompass_show(opts: KMirShowOpts) -> None:
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


def _run_build(opts: BuildOpts) -> None:
    assert isinstance(opts.project_dir, Path)
    cargo = CargoProject(opts.project_dir)

    _LOGGER.info('Rebuilding project with Cargo')
    _ = cargo.smir_for_project(opts.do_clean)


def _run_prove(opts: ProveOpts) -> None:
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
    if not proof.passed:
        sys.exit(1)


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
    _kompass_show(kmir_show_opts)


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
            _run_prove(opts)
        case ViewOpts():
            _run_view(opts)
        case ShowOpts():
            _run_show(opts)
        # ----- kmir functionality below
        case RunOpts():
            _kompass_run(opts)
        case ProveRawOpts():
            _kompass_prove_raw(opts)
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
