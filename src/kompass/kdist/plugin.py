from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pyk.kdist import kdist
from pyk.kdist.api import Target
from pyk.ktool.kompile import kompile

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any, Final

# MIR_SOURCE: Final = kdist.get('mir-semantics.source')
KSRC_DIR: Final = Path(__file__).parent / 'kompass'


class KSolanaKompileTarget(Target):
    _kompile_args: dict[str, Any]

    def __init__(self, kompile_args: Mapping[str, Any]) -> None:
        self._kompile_args = dict(kompile_args)

    def build(self, output_dir: Path, deps: dict[str, Path], args: dict[str, Any], verbose: bool) -> None:
        kompile_args = self._kompile_args

        includes: list[Path] = kompile_args.get('include_dirs', [])
        includes.append(kdist.get('mir-semantics.source') / 'mir-semantics')
        kompile_args['include_dirs'] = includes

        kompile(output_dir=output_dir, verbose=verbose, **kompile_args)

    def deps(self) -> tuple[str, ...]:
        return ('mir-semantics.source',)


__TARGETS__: Final = {'llvm': KSolanaKompileTarget({'main_file': KSRC_DIR / 'kompass.md', 'backend': 'llvm'})}
