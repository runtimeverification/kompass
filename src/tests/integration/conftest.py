from __future__ import annotations

import pytest
from kmir.kmir import KMIR
from pyk.kdist import kdist


@pytest.fixture
def kmir() -> KMIR:
    return KMIR(
        kdist.which('kompass.haskell'),
        kdist.which('kompass.llvm-library'),
    )
