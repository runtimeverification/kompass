# kompass

`kompass` is a CLI application that performs and manages symbolic execution and proofs of Rust programs for the Solana ecosystem using a Rust semantics written in [`K` Framework](https://kframework.org).

## Installation

#### Prerequsites: 
* `python >= 3.10`,
* `pip >= 20.0.2`,
* `uv >= 0.7.2` (other versions may work, too).

#### Build and installation from source

```bash
make build
pip install .
```

## Usage

`kompass` operates inside a cargo project to build and run/prove the code in it and view proof artifacts.  
For basic usage information, run `kompass --help` and inspect each command's available options with `kompass <command> --help`.

See [`Usage.md`](./Usage.md) for more detailed instructions including a small example program.

#### Prerequisites: 

`kompass` depends on [the K Framework Rust semantics `mir-semantics`](https://github.com/runtimeverification/mir-semantics)
and [the `stable-mir-json` plugin to `rustc`](https://github.com/runtimeverification/stable-mir-json).
Using `kompass` requires an installation of `stable-mir-json` (on the path under this exact name or installed in `$HOME`) 
and the build tool `cargo` (on the path under this exact name).

`kompass` is developed and tested on x86_64 platforms with Ubuntu Linux but _should_ work on other 64bit POSIX systems where `cargo` and `rustc` are available.

## For Developers

Use `make` to run common tasks (see the [Makefile](Makefile) for a complete list of available targets).

* `make build`: Build wheel
* `make check`: Check code style and formatting
* `make format`: Format code
* `make test`: Run tests

For interactive use, spawn a python interpreter with `uv run -- python3` (after `uv venv`).
