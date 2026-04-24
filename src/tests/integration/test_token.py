from __future__ import annotations

from pathlib import Path

import pytest
from kmir.kmir import KMIR, KMIRAPRNodePrinter
from kmir.options import ProveOpts as KMirProveOpts
from kmir.options import ShowOpts
from kmir.testing.fixtures import assert_or_update_show_output
from pyk.cterm.show import CTermShow
from pyk.kast.pretty import PrettyPrinter
from pyk.proof.show import APRProofShow

TOKEN_DATA_DIR = (Path(__file__).parent / 'data' / 'token').resolve(strict=True)

SPL_TOKEN_DIR = TOKEN_DATA_DIR / 'spl-token'
P_TOKEN_DIR = TOKEN_DATA_DIR / 'p-token'

SPL_TOKEN_PROVE_RS = list(SPL_TOKEN_DIR.glob('*.rs'))
P_TOKEN_PROVE_RS = list(P_TOKEN_DIR.glob('*.rs'))

TOKEN_PROVE_RS = SPL_TOKEN_PROVE_RS + P_TOKEN_PROVE_RS

START_SYMBOLS: dict[str, list[str]] = {
    'spl-multisig-iter-eq-copied-next-fail': ['repro'],
    'spl-multisig-signer-index': ['repro'],
}

SHOW_SPECS: list[str] = [
    'spl_token_domain_data-fail',
    'spl-multisig-iter-eq-copied-next-fail',
]


@pytest.mark.parametrize(
    'rs_file',
    TOKEN_PROVE_RS,
    ids=[f'{rs.parent.name}/{rs.stem}' for rs in TOKEN_PROVE_RS],
)
def test_token_prove_rs(rs_file: Path, kmir: KMIR, update_expected_output: bool) -> None:
    should_fail = rs_file.stem.endswith('fail')
    should_show = rs_file.stem in SHOW_SPECS

    if update_expected_output and not should_show:
        pytest.skip()

    start_symbols = START_SYMBOLS.get(rs_file.stem, ['main'])

    for start_symbol in start_symbols:
        prove_opts = KMirProveOpts(
            rs_file,
            start_symbols=[start_symbol],
            haskell_target='kompass.haskell',
            llvm_lib_target='kompass.llvm-library',
        )
        apr_proof = KMIR.prove_program(prove_opts)

        if should_show:
            printer = PrettyPrinter(kmir.definition)
            cterm_show = CTermShow(printer.print)
            display_opts = ShowOpts(
                rs_file.parent, apr_proof.id, full_printer=False, smir_info=None, omit_current_body=False
            )
            shower = APRProofShow(
                kmir.definition,
                node_printer=KMIRAPRNodePrinter(cterm_show, apr_proof, display_opts),
            )
            show_res = '\n'.join(shower.show(apr_proof))
            expected_file = rs_file.parent / f'show/{rs_file.stem}.{start_symbol}.expected'
            expected_file.parent.mkdir(exist_ok=True)
            assert_or_update_show_output(
                show_res,
                expected_file,
                update=update_expected_output,
            )

        if not should_fail:
            assert apr_proof.passed, f'Expected proof to pass for {rs_file.stem}::{start_symbol}'
        else:
            assert apr_proof.failed, f'Expected proof to fail for {rs_file.stem}::{start_symbol}'
