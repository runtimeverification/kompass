from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from kmir.__main__ import _arg_parser, _parse_args
from kmir.cargo import CargoProject
from kmir.options import ProveRawOpts, ProveRSOpts, PruneOpts, RunOpts, ShowOpts, ViewOpts
from kmir.smir import SMIRInfo
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

    smir_file: Path
    if opts.file:
        smir_file = Path(opts.file)
    else:
        cargo = CargoProject(Path.cwd())
        target = opts.bin if opts.bin else cargo.default_target
        smir_file = cargo.smir_for(target)

    smir_info = SMIRInfo.from_file(smir_file)

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


def kompass(args: Sequence[str]) -> None:
    parser = _arg_parser()
    parser.prog = 'kompass'
    ns, remaining = parser.parse_known_args(args)
    logging.basicConfig(level=_loglevel(ns), format=_LOG_FORMAT)

    opts = _parse_args(ns)
    match opts:
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
