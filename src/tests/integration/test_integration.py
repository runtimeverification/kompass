from __future__ import annotations

from pathlib import Path
from tempfile import mkstemp

import pytest
from kmir.testing.fixtures import assert_or_update_show_output

import kompass.__main__ as main
from kompass.options import BuildOpts, ProveOpts, ShowOpts

TEST_CRATES_DIR = (Path(__file__).parent / 'data').resolve(strict=True)
TEST_CRATES = list(TEST_CRATES_DIR.glob('*/main-crate'))


@pytest.mark.parametrize(
    'main_crate',
    TEST_CRATES,
    ids=[spec.parent.stem for spec in TEST_CRATES],
)
def test_multi_crate_exec(main_crate: Path, update_expected_output: bool) -> None:
    # call CLI methods with build, then prove and show for all start-symbols

    # kompass build
    build_opts = BuildOpts(main_crate, do_clean=True)
    main._run_build(build_opts)

    for expectation in main_crate.glob('*.expected'):
        sym = expectation.name.removesuffix('.expected')

        if sym.endswith('.fail'):
            expect = False
            start = sym.removesuffix('.fail')
        else:
            expect = True
            start = sym

        # kompass prove --start-symbol sym
        prove_opts = ProveOpts(main_crate, start, max_iterations=2)

        result = main._run_prove(prove_opts)
        assert result == expect, f'Unexpected proof outcome {result} for {sym}'

        # kompass show f'linked.smir.{sym}' -o temp-file
        _, tmp = mkstemp(prefix=sym)
        show_opts = ShowOpts(main_crate, None, f'linked.smir.{start}', output=Path(tmp))
        main._run_show(show_opts)

        # compare or update output
        with open(tmp, 'r') as f:
            actual = f.read()
            actual = '\n'.join([line for line in actual.splitlines() if not 'span:' in line])
        assert_or_update_show_output(
            actual,
            expectation,
            update=update_expected_output,
        )
