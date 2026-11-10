# nsh-py on the web (preview)

nsh-py apps run in a browser: Pyodide runs the Python, and NSH's DOM
backend renders it, with Python handlers, signals, `@nsh.computed`,
`nsh.table`, `nsh.card` and timers. The same app file runs on desktop and
on the web. NSH 0.4.0, Pyodide 314.0.7, stable Rust. Not a supported
target yet: no wheels, no CI.

**Waiting on NSH:** `nsh-core` 0.4.0 doesn't compile for emscripten (it
uses `libc` under `cfg(unix)` but only depends on it off wasm32, and
emscripten is both). The one-line fix is merged upstream
([longbridge/nsh#896](https://github.com/longbridge/nsh/pull/896)) but
in no release yet. We don't patch NSH, so `build.sh` refuses to run on
0.4.0. Once a release has the fix: bump the pins, drop the check in
`build.sh`, and the build works as below. Until then, the branch
`spike/web` has a local patch for trying it.

## Try it (after the next NSH release)

```sh
sh web/pyodide/build.sh                      # one-time setup: see the script's header
python3 -m http.server -d web/pyodide/site 8766
# http://localhost:8766/                      the counter (site/counter.py)
# http://localhost:8766/?app=examples/poll.py any of the repo's examples
```

## How it works (`web/pyodide/`)

The whole extension (PyO3 + NSH core/engine/base + `nsh-platform-web`) is
built as one Pyodide side module (`wasm32-unknown-emscripten`). In the page:

1. Pyodide loads; `micropip` installs the wheel.
2. A hook on `WebAssembly.instantiate` adds NSH's `nsh` imports (text
   measuring, fonts, `submit`, `request_pump`, ...) when Pyodide
   instantiates the extension, and keeps the instance.
3. A patched copy of `nsh.js` (`site/nsh.js`, one `instantiate` option in
   `Player.load`) adopts that instance instead of loading its own module;
   its memory is Pyodide's.
4. The app runs (`counter.py`, or `?app=examples/<name>.py`: `build.sh`
   copies `examples/` next to the page): on the web `nsh.run()` registers
   the root with `nsh_platform_web::set_root`, starts the engine queue and
   returns. `player.runRust()` starts it; the engine runs on the page's
   main thread (`LocalEngine`), pumped by JS.

Verified in a browser (Pyodide 314.0.7 and, before the toolchain switch,
0.29.5): the counter's +1/−1 call the Python handlers and the bound text
and `class_` update; in the poll, voting re-sorts the table and updates
the vote count; `nsh.set_interval`/`set_timeout` fire, and
`nsh.call_soon` called before the app starts runs once its pump does.

## NSH 0.4.0 port (2026-11-10)

What changed from the 0.3.0 spike:

- **`nsh.js`.** 0.4.0 rewrote the player (`runModule`, a browser JS
  host, side modules), but `Player.load` still builds the import object
  and then compiles and instantiates: the hook is the same one
  `instantiate` option around that part. `runRust()` is unchanged.
- **Engine queue and timers** (new on main): no changes needed. The queue
  is a `Mutex` and a `Waker`, which work without threads; waking the pump
  asks the page for an `nsh_pump`. `nsh.run()` on the web now calls
  `queue::begin()` so jobs posted before the page starts the app wait for
  it. Top-level Python run by the page is not "in the engine", so its
  signal writes go through the queue, as from a worker thread on desktop.
- **libc.** `nsh-core` 0.4.0 still has the bug. `spike/web` patches a
  local copy (`[patch.crates-io]`); `main` waits for a release.
- **Toolchain: now stable.** Pyodide 314.0.7 (Python 3.14, emscripten
  5.0.3, ABI `pyemscripten_2026_0`) and the repo's pinned Rust 1.99.1 with
  its `wasm32-unknown-emscripten` target. No nightly, no `-Zbuild-std`,
  no custom sysroot. pyodide-build must run on Python 3.14. maturin 1.16
  writes the PEP 783 tag. ABI checks on the module: legacy wasm
  exceptions (`try`, no `try_table`), no `invoke_*`, `emscripten_longjmp`
  or `__wasm_setjmp` imports. Pyodide's own Rust pin is 1.93.0; 1.99.1
  works too.

| Build | Toolchain | Module | Brotli | Wheel |
|---|---|---|---|---|
| NSH 0.3.0 (before) | nightly + build-std, Pyodide 0.29.5 | 12.8 MB | 3.2 MB | 4.6 MB |
| NSH 0.4.0 | nightly + build-std, Pyodide 0.29.5 | 20.2 MB | 4.0 MB | 6.3 MB |
| NSH 0.4.0 (now) | stable 1.99.1, Pyodide 314.0.7 | 20.3 MB | 4.1 MB | 6.4 MB |

The +60% comes from NSH 0.4.0 itself (more nsh-base parts, math
typesetting, HTML parsing, syntax highlighting), all linked because
`nsh_base::registry()` registers everything. Still no size work at all
(release profile is `lto = "thin"`, no `opt-level = "s"`, no wasm-opt).
A cold release build takes about 3 minutes.

## What's left

- **Size.** 0.4.0's nsh-base has `parts` and `registry_of(..)`, so a
  web-only registry of the parts nsh-py uses no longer needs a patched
  nsh-platform-web. Then a size profile and wasm-opt (`web/PLAN.md`).
- **The libc fix:** an NSH release with #896 (see the top).
- **`nsh.js` patch.** To propose upstream (an "adopt this instance"
  option), or keep a tiny loader of our own.
- **Not done:** headless tests on wasm (nsh-testing's driver is off
  there); a panic-to-exception test; the page hook should become a small
  JS loader we ship (`nsh-py.js`); `nsh.run()` options (title, size) are
  ignored on the web; one app per page (the root is taken once); dark
  mode, fonts and assets untested; Python's `KeyboardInterrupt` n/a.
- **Testing note:** the preview browser's coordinate and text-selector
  clicks didn't reach NSH's buttons in the poll; accessibility-ref clicks
  and dispatched pointer events did.
