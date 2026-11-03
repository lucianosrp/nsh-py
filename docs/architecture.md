# nsh-py architecture

nsh-py binds NSH's public Rust app API through PyO3 ("Path B" in
`CLAUDE.md`; the full reasoning is in `docs/research/nsh-2026-11-03.md`).
This page covers how the pieces fit and the decisions behind them.

## Layers

```
python/nsh/            pure Python: the API users see
  _elements.py         Element, view(), text(), button()  (plain objects)
  _signals.py          signal(), Signal
  _runtime.py          run(), report_exception()
src/                   Rust (the _core extension module)
  app.rs               run(): the window, the root component, Ctrl-C
  tree.rs              Python Element trees -> NSH elements
  bridge.rs            calling Python from the engine thread, error logging
  signal.rs            Trigger: the NSH signal behind each Python signal
```

Elements are **plain Python objects** (`kind`, `props`, `children`), not Rust
objects. Most sprint work (styled components, new props, docs) is therefore
Python only, and a future Streamlit-style layer can build the same objects.
`tree.rs` turns them into NSH elements when the app runs, on the engine
thread.

## Threads

```
Python main thread ── nsh.run(App) ──► Rust: py.detach (GIL released) → platform::run_app
                                       │  GTK/AppKit/Win32 main loop
                                       │  100 ms GLib timer: Python::attach → check_signals (Ctrl-C)
engine thread "nsh-engine" ──► AppRoot::view → Python App() → Element tree → NSH elements
                               bindings, regions, on_press → bridge::call → Python::attach
```

- `run_app` owns the main thread until the window closes, so `nsh.run()`
  blocks, like `tkinter.mainloop()`.
- All app code runs on the engine thread. NSH's reactive graph is
  thread-local and panics anywhere else.
- **Ctrl-C:** Python's SIGINT handler only sets a flag. `check_signals`
  runs it on the main thread, which is busy in the GTK loop, so a GLib
  timer checks every 100 ms. On `KeyboardInterrupt` it quits the
  `gio::Application`, and `nsh.run()` re-raises it. macOS and Windows
  don't have this yet (they need an AppKit/Win32 timer).
- **Errors:** every call from NSH into Python goes through `bridge::call`.
  An exception is logged on the `nsh` logger (with a traceback, even when
  logging isn't configured) and the app keeps running. A failed handler
  does nothing, a failed binding shows an empty string, and a root that
  raises shows an error page.

## Signals: decision

The spike had to choose between two designs:

- **A. NSH `Signal<PyObject>`:** the value lives in an NSH signal.
- **B. Python-side signals driving `dynamic`:** a pure-Python signal, with
  `dynamic` regions re-made when it changes.

**We chose a hybrid: the value lives in Python, and NSH tracks the
dependencies.** Each `nsh.signal` holds a `Trigger`, an NSH
`Signal<()>` with `SignalEquals::Never` that has no value of its own:

- `count()` returns the Python value and, inside the engine, reads the
  trigger, which subscribes whatever NSH computation is running (a text
  binding, a `class_` binding, a callable child).
- `count.set(v)` stores `v` and, if `v != old`, writes the trigger. NSH
  re-runs exactly the bindings that read it.

Why not A, the value in NSH:

- Every read and write would cross into Rust and clone a `Py<PyAny>`, and
  equality would need the GIL inside NSH's `PartialEq`. With the hybrid,
  equality is Python's own `==`, guarded for objects like NumPy arrays
  whose `==` doesn't return a bool.
- An NSH signal can only exist inside the engine. Python signals have to
  work everywhere: at module level, in unit tests with no app, and in
  future Streamlit-style code. The trigger is created lazily, on the first
  read inside the engine. Outside it, a signal is just a box.

Why not B, Python signals plus `dynamic`:

- Python would need its own dependency graph to know *which* regions to
  re-run. Without one, every change re-makes the whole tree under a
  `dynamic`, which loses input focus and text-field state and is slow.
  NSH already has a fine-grained graph (Solid-style), and the trigger
  reuses it, including batching, ownership and disposal.
- B adds nothing A or the hybrid can't do: a callable child is still a
  `dynamic` region when you want one.

Details:

- The trigger lives under its own `create_root` owner. A binding that
  first read it doesn't own it, so re-running that binding can't dispose
  it. It's disposed when the Python `Signal` is dropped on the engine
  thread. Dropped elsewhere, one empty graph slot leaks until the app ends.
- `Trigger` uses `Cell`, not `&mut self`: reading a signal can make NSH
  run bindings that read the same signal again, so it's re-entrant.
- **Pitfall 1** (a read outside a lambda isn't reactive):
  `nsh.text(f"{count()}")` is read once. Write `nsh.text(lambda: ...)`, or
  pass the signal itself: `nsh.text(count)`. A lint or warning is still
  to do.
- **Pitfall 2** (in-place mutation): `items().append(x)` changes nothing
  the signal can see. `items.mutate(lambda xs: xs.append(x))` changes the
  value in place and always notifies.
- **Writes from other threads** (a Python worker thread) can't notify yet:
  the value changes, the UI doesn't, and a warning is logged. The fix is to
  post the write to the engine thread. That's a next step.
- `computed` and `effect` aren't there yet. A plain lambda already acts as
  an uncached computed. Cached ones map onto NSH `computed`/`effect` with
  the same trigger approach.
