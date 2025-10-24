Using `kompass` to run proofs of Rust functions for Solana
----------------------------------------------------------

The `kompass` tool provides a way to prove that a given function in a Rust program
* does not exhibit undefined behaviour, and
* runs to completion with any type-correct input.
The execution flow of the function can be inspected as a control flow graph.

# Setup

## Docker-based

The easiest way to set up `kompass` is by using a dedicated docker image where the tools are pre-installed.

At the time of writing, the `kompass` docker image itself needs to be built and installed
but we will publish the `kompass` docker image to docker hub in the near future.

To build the docker image with a tag `kompass:local`, use the following command in a local checkout of `kompass`:

```shell
/path/to/kompass$ docker build -t kompass:local --build-arg KMIR_VERSION=$(cat deps/kmir_release) .
```



## Manual Installation

If docker is not available, one can set up the tool chain and its prerequisites manually with the following steps:

* Install `rustup` (with a default `rustc` and `cargo`)
    ```shell
    $ curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    ```
    This provides `rustc` and `cargo` in default versions.
* Install `stable-mir-json` from source, using the following commands:
    ```shell
    $ git clone https://github.com/runtimeverification/stable-mir-json
    $ cd stable-mir-json
    $ cargo build --release && cargo run --bin cargo_stable_mir_json $PWD
    ```
    This creates `$HOME/.stable-mir-json` into
* Install `K`, best done using using `kup`.
    ```shell
    $ bash <(curl https://kframework.org/install)
    $ kup install k
    ```
    This installs the latest version of `K` framework, including the `kompile` command as well as
    the symbolic backend required for the proofs, and a number of other `K` tools.
    The installation of `K` is `nix`-based, so `nix` will be installed unless it is already available.
* Download and build `kompass`

    `kompass` requires an installation of `python3` (`>= 3.10`) and `uv` to build.
    `python3` may already be present, or it can be installed using the package manger of your system.
    After checking that `python3` is available, install `uv` with:
    ```shell
    $ python3 --version
    Python 3.11.6 # example output
    $ curl -LsSf https://astral.sh/uv/0.7.2/install.sh | sh
    ```

    Then download and build `kompass` itself using the following commands:
    ```shell
    $ git clone https://github.com/runtimeverification/kompass
    $ cd kompass
    $ make build
    ```

    To run the `kompass` tool, the path to the `kompass` checkout must be provided:

    ```shell
    ...some/other/directory$ uv --project path/to/kompass run -- kompass --help
    ```
    A shell alias can make this easier:
    ```shell
    $ cd path/to/kompass
    $ alias kompass="uv --project $PWD run -- kompass"
    $ cd .../some/other/directory
    $ kompass --help
    ```

### Uninstalling
* The `kompass` tool is not installed but run from its repository without modifying the system.
* `K` and `nix` can be uninstalled by removing the multi-user `nix` installation, as [described in the `nix` manual](https://nix.dev/manual/nix/latest/installation/uninstall.html).
* Uninstalling the `pip` and `uv` tools is not recommended. Please refer to their respective manuals for removal.
* To uninstall `stable-mir-json`, simply delete it from the `$HOME`: `rm -rf $HOME/.stable-mir-json`
* Removing `rustup` is not recommended. To uninstall `rustup`, run `rustup self uninstall`

# Using `kompass`

`kompass` works with Rust code set up in `cargo` projects.
Either `kompass` is called from the cargo project directory (or the directory can be specified using `--project DIR` or `-C DIR`).

The following code is a straightforward Rust executable for demonstration:

```shell
.../small-test$ ls
Cargo.lock  Cargo.toml  src  target
.../small-test$ more src/main.rs
pub fn add(left: u64, right: u64) -> u64 {
    left + right
}

pub mod a_module {
    use super::add;

    pub fn twice(x: u64) -> u64{
        add(x, x)
    }
}

pub fn main() {
    let x = 42;
    assert_eq!(a_module::twice(x), 2 * x);
}
```

The `main` function won't have any problem, but `a_module::twice` cannot be called with numbers larger than 2^31 because the `add` function may overflow.

## Building the project with `kompass build`

Before running proofs, the `cargo` project must be built with `kompass build`.
```shell
.../small-test$ kompass build --verbose
INFO 2025-06-19 14:16:15,699 kompass.__main__ - Rebuilding project with Cargo
INFO 2025-06-19 14:16:15,699 kmir.cargo - Running "cargo build" with stable-mir-json in .../small-test
INFO 2025-06-19 14:16:15,903 kmir.cargo -    Compiling small_test v0.1.0 (.../small-test)
INFO 2025-06-19 14:16:15,904 kmir.cargo -     Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.16s
INFO 2025-06-19 14:16:15,905 kmir.linker - Maximum type ID (offset) is 100, linking 1 smir.json files
```
This runs `cargo build` (in default debug mode) and creates a `linked.smir.json` file in the project's `target` directory.
Optionally, one can add `--rebuild` to run `cargo clean` before (**NOTE:** This will discard data from all proofs run before!).
The `--verbose` flag provides more information about what is happening behind the scenes.

## Running a given function with symbolic input with `kompass prove`

To run a given function from the code in the `cargo` project, use
```shell
.../small-test$ kompass prove
WARNING 2025-06-19 14:16:22,346 kmir.smir - Could not find sym in fun_syms: _ZN3std2rt10lang_start17h3877dc8469262e28E
WARNING 2025-06-19 14:16:22,346 kmir.smir - Could not find sym in fun_syms: _ZN4core3ops8function6FnOnce40call_once$u7b$$u7b$vtable.shim$u7d$$u7d$17h2286ad0ee4e3ac0cE
WARNING 2025-06-19 14:16:22,346 kmir.smir - Could not find sym in fun_syms: _ZN4core3ptr85drop_in_place$LT$std..rt..lang_start$LT$$LP$$RP$$GT$..$u7b$$u7b$closure$u7d$$u7d$$GT$17h5379b28d388f7714E
APRProof: linked.smir.main
    status: ProofStatus.PASSED
    admitted: False
    nodes: 3
    pending: 0
    failing: 0
    vacuous: 0
    stuck: 0
    terminal: 2
    refuted: 0
    bounded: 0
    execution time: 0s
Subproofs: 0
```
By default, the `main` function is executed, and it terminates successfully here (`ProofStatus.PASSED`, as expected).

Other functions can be executed using `--start-symbol`, and will use symbolic arguments if they take any.

The following command executes the code of the Rust function named `twice` in module `a_module` with one symbolic arguments.
Function names are prefixed with the respective module names where they reside, separated by double colons (`::`).

```shell
.../small-test$ kompass prove --start-symbol a_module::twice
WARNING 2025-06-19 14:16:39,721 kmir.smir - Could not find sym in fun_syms: _ZN3std2rt10lang_start17h3877dc8469262e28E
WARNING 2025-06-19 14:16:39,721 kmir.smir - Could not find sym in fun_syms: _ZN4core3ops8function6FnOnce40call_once$u7b$$u7b$vtable.shim$u7d$$u7d$17h2286ad0ee4e3ac0cE
WARNING 2025-06-19 14:16:39,721 kmir.smir - Could not find sym in fun_syms: _ZN4core3ptr85drop_in_place$LT$std..rt..lang_start$LT$$LP$$RP$$GT$..$u7b$$u7b$closure$u7d$$u7d$$GT$17h5379b28d388f7714E
APRProof: linked.smir.a_module::twice
    status: ProofStatus.FAILED
    admitted: False
    nodes: 7
    pending: 0
    failing: 1
    vacuous: 0
    stuck: 1
    terminal: 2
    refuted: 0
    bounded: 0
    execution time: 0s
Subproofs: 0
```

This execution halts on a construct that caused undefined behaviour, leaving one node `stuck` and the proof fails.
Typically, one would execute functions which test the behaviour of other code by applying assertions on the results to confirm desired properties (as code for fuzzing usually does) to check properties beyond undefined behaviour.

Proof artifacts are stored in the project's `target` directory, under `proofs`.

```shell
/small-test$ ls target/proofs/
linked.smir.a_module::twice  linked.smir.main
```

## Inspecting the execution flow of a proof

After executing the proof above, one can inspect the execution using `kompass show` or `kompass view`.
The `show` command outputs the execution tree as text, while `view` starts an interactive viewer for more detailed inspection.
Both commands support the `--full` option to print all details, but will only output the most important parts of the machine state by default.

```shell
.../small-test$ kompass show 'linked.smir.a_module::twice'

┌─ 1 (root, init)
│   #execTerminator ( terminator ( ... kind: terminatorKindCall ( ... func: operandC
│   span: 0
│
│  (42 steps)
├─ 3 (split)
│   #expect ( typedValue ( BoolVal ( notBool ARG_UINT1:Int +Int ARG_UINT1:Int &Int 1
│   function: add
┃
┃ (branch)
┣━━┓ subst: .Subst
┃  ┃ constraint:
┃  ┃     notBool notBool ARG_UINT1:Int +Int ARG_UINT1:Int &Int 18446744073709551615 ==Int ARG_UINT1:Int +Int ARG_UINT1:Int ==Bool false
┃  │
┃  ├─ 4
┃  │   #expect ( typedValue ( BoolVal ( notBool ARG_UINT1:Int +Int ARG_UINT1:Int &Int 1
┃  │   function: add
┃  │
┃  │  (2 steps)
┃  └─ 6 (stuck, leaf)
┃      #ProgramError ( AssertError ( assertMessageOverflow ( binOpAdd , operandCopy ( p
┃      function: add
┃
┗━━┓ subst: .Subst
   ┃ constraint:
   ┃     notBool ARG_UINT1:Int +Int ARG_UINT1:Int &Int 18446744073709551615 ==Int ARG_UINT1:Int +Int ARG_UINT1:Int ==Bool false
   │
   ├─ 5
   │   #expect ( typedValue ( BoolVal ( notBool ARG_UINT1:Int +Int ARG_UINT1:Int &Int 1
   │   function: add
   │
   │  (21 steps)
   ├─ 7 (terminal)
   │   #EndProgram ~> .K
   │   function: a_module::twice
   │
   ┊  constraint: true
   ┊  subst: ...
   └─ 2 (leaf, target, terminal)
       #EndProgram ~> .K
```

We can see that on the failing branch with `#ProgramError` (in the middle), the argument `ARG_UINT1` was too large,
such that its double was larger than 18446744073709551615 (2^64 - 1), i.e., the addition overflowed and the program errored.
On the other branch (at the bottom), the sum stayed in range and the function finished successfully.
