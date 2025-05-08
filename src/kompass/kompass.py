from __future__ import annotations

from typing import TYPE_CHECKING

from kmir.kmir import KMIR
from pyk.kdist import kdist

if TYPE_CHECKING:
    from typing import Final

LLVM_DEF_DIR: Final = kdist.which('kompass.llvm')
LLVM_LIB_DIR: Final = kdist.which('kompass.llvm-library')
HASKELL_DEF_DIR: Final = kdist.which('kompass.haskell')


class Kompass(KMIR): ...
