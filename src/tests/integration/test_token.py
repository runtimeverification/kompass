from __future__ import annotations

from pathlib import Path

import pytest
from kmir.kmir import KMIR
from kmir.options import ProveRSOpts

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


@pytest.mark.parametrize(
    'rs_file',
    TOKEN_PROVE_RS,
    ids=[f'{rs.parent.name}/{rs.stem}' for rs in TOKEN_PROVE_RS],
)
def test_token_prove_rs(rs_file: Path) -> None:
    should_fail = rs_file.stem.endswith('fail')

    start_symbols = START_SYMBOLS.get(rs_file.stem, ['main'])

    for start_symbol in start_symbols:
        prove_rs_opts = ProveRSOpts(
            rs_file,
            start_symbol=start_symbol,
            haskell_target='kompass.haskell',
            llvm_lib_target='kompass.llvm-library',
        )
        apr_proof = KMIR.prove_rs(prove_rs_opts)

        if not should_fail:
            assert apr_proof.passed, f'Expected proof to pass for {rs_file.stem}::{start_symbol}'
        else:
            assert apr_proof.failed, f'Expected proof to fail for {rs_file.stem}::{start_symbol}'
