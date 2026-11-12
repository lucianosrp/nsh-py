# nsh-py architecture

nsh-py binds NSH's public Rust app API through PyO3 ("Path B" in
`AGENTS.md`; the full reasoning is in `docs/research/nsh-2026-11-03.md`).
This page covers how the pieces fit and the decisions behind them.

## Layers and where code goes

**The rule: behaviour goes in Rust, look and composition go in Python.**

```
python/nsh/
  __init__.py          public API: re-exports only
  primitives/          one module per Rust element kind (view.py, text.py) ← pairs with src/elements/
  components/          Python-only styled components (button.py)            ← most contributions
  _element.py          Element, props(), merge_class()                       ┐
  _signals.py          signal(), Signal                                      │ core
  _each.py             each(): keyed lists (a marker, not a kind)            │
  _runtime.py          run(), report_exception()                             │ (maintainers)
  _engine.py           call_soon, effect, set_timeout, set_interval          │
  testing.py           headless apps for tests                               ┘
src/
  elements/            one file per kind (view.rs, text.rs); mod.rs has the KINDS table
  props.rs             props many kinds share (class_, on_press, role, test_id)
  tree.rs              walks children: elements, strings, lists, callables (regions)
  each.rs              nsh.each as NSH's keyed `each` region
  bridge.rs            calling Python from the engine thread, error logging  ┐
  signal.rs            Trigger: the NSH signal behind each Python signal     │ core
  queue.rs             the engine-thread queue: call_soon, posting jobs      │
  schedule.rs          Effect and Timer: NSH effects and timers for Python   │
  app.rs               run(): the window, the root component, Ctrl-C         │
  headless.rs          nsh-testing's driver for nsh.testing                  ┘
tests/
  primitives/, components/   one test file per primitive / component (headless)
  test_kinds.py              Python primitives == Rust kinds
```

| Change | Where | Rust? |
|---|---|---|
| A styled component built from primitives | `components/<name>.py` | no |
| A new prop on a primitive | `src/props.rs` or `src/elements/<kind>.rs`, plus the Python function | a little |
| A new primitive or an nsh-base component with behaviour (input, dialog) | `src/elements/<kind>.rs` + `KINDS`, plus `primitives/<kind>.py` | yes |
| Signals, threads, runtime | core | maintainers |

Elements are **plain Python objects** (`kind`, `props`, `children`), not Rust
objects. The `kind` string and the `props` dict are the whole contract
between the layers: `src/elements/<kind>.rs` reads the props its Python
function writes. `tests/test_kinds.py` fails if the two lists of kinds
drift apart. A future Streamlit-style layer builds the same objects.

Core rules for Rust code: call Python only through `bridge::call` (it
logs exceptions); touch NSH only on the engine thread; never hold the GIL
while waiting on the engine (`py.detach`).

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
- **Other threads:** any Python thread can reach the app through the
  engine-thread queue (next section). `nsh.call_soon(fn, *args)` runs `fn`
  on the engine thread, and signal writes use it.
- **Errors:** every call from NSH into Python goes through `bridge::call`.
  An exception is logged on the `nsh` logger (with a traceback, even when
  logging isn't configured) and the app keeps running. A failed handler
  does nothing, a failed binding shows an empty string, and a root that
  raises shows an error page.

## The engine-thread queue

NSH's graph is thread-local, so a worker thread can't write a signal's
trigger, make an effect or free a trigger's graph slot. It posts a job to
the engine instead (`src/queue.rs`):

- **The pump.** The root component spawns one long-lived NSH task. Each
  time it is polled it runs the jobs queued so far, each marked
  inside the engine (`bridge::enter`), then returns `Pending`. A task's
  `Waker` is `Send` and waking it wakes the engine's loop on any thread
  (`nsh-core`'s executor: "wakers may fire on any thread"), so a post is
  `push job; waker.wake()`. No channel into the engine is needed, and the
  headless driver (`nsh-testing`) sees the work as engine activity, so
  `app.wait_for` waits for it.
- **Order and fairness.** Jobs run in the order posted. A poll runs only the
  jobs there were when it started and wakes itself if more arrived, so a
  job that keeps posting can't starve the loop. A job posted from the
  engine thread itself runs after the current handler, never inside it.
- **States.** The queue is global (one app per process) and is *Idle* (no
  app), *Starting* (`nsh.run` / `nsh.testing.open` began and the pump isn't
  there yet: jobs wait) or *Running* (the pump holds the waker). `run()` and
  `Headless` set it up and tear it down; when the pump task ends with its
  owner the state goes back to Starting, and a pump that finishes after
  `end()` can't revive it.
- **No app.** With the queue Idle, `post` refuses. `nsh.call_soon` then runs
  the function right away on the calling thread (there is no engine to wait
  for, and a script that calls it before `nsh.run` shouldn't silently lose
  the call). Jobs still queued when the app ends are dropped. A call made
  while an app is *Starting* waits for it.
- **Rules kept.** Posting takes a short lock and never waits for the
  engine; the lock is never held while running or dropping a job, so
  dropping a job's Python references can't deadlock. Python is only called
  through `bridge::call`.
- **Triggers dropped off the engine** (a `Signal` freed on a worker thread)
  post their owner's disposal. With no app the graph is gone already.

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
  it. It's disposed when the Python `Signal` is dropped: at once on the
  engine thread, posted there from any other thread (with no app running
  the graph is gone already).
- `Trigger` uses `Cell`, not `&mut self`: reading a signal can make NSH
  run bindings that read the same signal again, so it's re-entrant.
- **Pitfall 1** (a read outside a lambda isn't reactive):
  `nsh.text(f"{count()}")` is read once. Write `nsh.text(lambda: ...)`, or
  pass the signal itself: `nsh.text(count)`. A lint or warning is still
  to do.
- **Pitfall 2** (in-place mutation): `items().append(x)` changes nothing
  the signal can see. `items.mutate(lambda xs: xs.append(x))` changes the
  value in place and always notifies.
- **Writes from other threads** (a Python worker thread) store the value
  at once and post the notify to the engine (`_Source._changed`): the
  computeds downstream are marked stale and the triggers notified there, in
  one NSH `batch` so a binding that reads a computed and its signal runs
  once. The UI follows soon. `set`, `update` and `mutate` hold a per-signal
  lock while they read and store, so concurrent `update`s from a worker and
  the app lose nothing. `fn` in `update` and `mutate` runs on the calling
  thread, under the lock: keep it short. With no app running the notify
  runs right where it is called. Reading computeds from worker threads is
  not made safe (they compute on whichever thread reads them first): read
  them in bindings, effects or posted calls.
- **`computed`** caches in Python. While it computes, it records the
  signals it reads (a thread-local stack), and they hold it in a
  `WeakSet`. A write marks every computed downstream stale, then notifies
  their triggers along with the signal's own, so NSH re-runs the bindings
  that read them. A stale computed recomputes on its next read (lazy, so
  no half-updated values). This is a small Python graph for caching only;
  which bindings re-run is still NSH's call. A plain lambda remains an
  uncached computed.
- **Styles are interchangeable:** a lambda, a named function, a computed
  or a signal can go anywhere a binding goes, and `count.updater(fn)`,
  `count.mutator(fn)` and `count.setter(v)` just return zero-argument
  handlers. Nothing in Rust knows about them.
- **`effect`** is an NSH effect made on the engine (`schedule.rs`
  `Effect`): it runs a Python function now and again when the triggers it
  read notify. The Python side reads signals as usual (`count()` subscribes
  the running effect). It lives in an owner of its own (so `.dispose()`
  works) that the current owner disposes with a cleanup: a component's effect
  ends with the component, a handler's with its element, a posted one with
  the app's root. Made on another thread, it's posted, so its first run
  isn't immediate; `dispose()` from any thread is posted too (a disposal
  before the creation ran wins). **With no app** (a plain script, or before
  `nsh.run`) the effect is Python only (`_engine.py`): a computed that
  records what it reads as it reads, and is run again by `_notify` after the
  downstream computeds are marked stale, on the writing thread. It's kept
  alive until disposed, and stopped with an error if it keeps changing what
  it reads (100 runs). It isn't tied to a component, so an effect made
  before `nsh.run` stays Python only for good.
- **Timers** (`set_timeout`, `set_interval`) are NSH tasks that wait on the
  executor's timers (`schedule.rs` `Timer`), owned like effects. The handle
  only holds an atomic flag, so `cancel()` works from any thread without
  the queue: the callback stops being called at once, and the task ends
  when it next wakes. They need a running app (`RuntimeError` otherwise).

## Class components: `nsh.Component`

Sugar over function components, not a second model (`_component.py`).
A metaclass makes `Counter(**props)` run `setup()` then `view()` once and
return the elements, so a class goes anywhere a function component does.
Each annotated class attribute becomes a descriptor over one signal per
instance: reading `self.count` is `signal()` (tracked), assigning is
`.set()`. Props set the starting values; a `Signal` passed as a prop is
used as is (shared state). Hot reload keys the fields by the class
(`_signal_hook(value, (where, instance))`) instead of the stack, which
would point at `_component.py` for every class.

**Why not React-style `render()`.** Re-running the whole view on each
change costs in proportion to the tree and drops native state (focus,
cursor, scroll). Measured headless, one changed number among N rows:
function and class components both make 1 Python call per update;
re-rendering makes N, and takes 2-7x the CPU per update at 10-1000 rows.
The object itself costs ~65 ns more than a function call, once per
mount; a field read ~100 ns more than calling the signal.

## Keyed lists: `nsh.each`

`nsh.each(items, render, key=...)` binds NSH's `each` (flow.rs). A
callable child re-makes every row on every change; `each` renders only
new keys, keeps rows whose key stays (moving them on reorder, with their
nodes, bindings and the signals `render` made) and disposes the rest.

- **Not an element kind.** It has no node or props of its own: like a
  callable child, it's a region of its parent's children. So it's a
  marker object (`nsh._each.Each`) that `tree.rs` hands to `each.rs`, and
  `KINDS`/`tests/test_kinds.py` don't list it.
- **Keys.** NSH wants `K: Hash + Eq + Clone`. The Python key is computed
  with the items in one GIL pass (the items binding), with its `hash()`;
  equality is Python's `==` asked under the GIL (`Python::attach`, an
  exception meaning "not equal"), so keys behave like dict keys. Python
  objects sit behind an `Rc`, so NSH clones them without the GIL. A key
  that raises (or isn't hashable) is logged and replaced by a unique key.
- **Default key: the item itself** (strings, numbers, tuples), or its
  identity when it's unhashable (dicts): no copy-and-compare surprises
  for values, and records kept as the same objects still match. Records
  that are rebuilt (`{**todo, "done": True}`) need `key=`.
- **Items.** NSH gives each row its item as a signal, set when an item
  under the same key changes (`is`, then `==`). The row's Python `render`
  runs untracked inside a `dynamic` that reads only that signal: it runs
  once per key, and again (in place) only if the item under the key was
  replaced by one that isn't `==`. Signals read in `render` are read once,
  as in a component.
- **Index.** `render(item)` is enough. With `index=True` it is
  `render(item, index)`: the second argument is a callable wrapping
  NSH's index signal: `index()` is the row's position, and a binding that
  reads it updates when the row moves, without rendering again. Pass it
  as a binding (`nsh.text(index)`) or call it in one
  (`nsh.text(lambda: f"{index()}. {item}")`). It's a flag rather than a
  look at `render`'s signature, which can't tell for `*args`, builtins
  or decorated functions.
- **Errors.** `items`, `key` and `render` run through `bridge::call`. A
  failed `items` keeps the rows shown (the last good list), so their state
  survives an error that may pass.

## Binding nsh-base components

`checkbox`, `switch` and `progress` are nsh-base components (`Checkbox`,
`Switch`, `Progress`), not host elements like `view` or `input`. Tabs,
tooltips and dialogs will be bound the same way, so here is the recipe
and what is different.

- **Build it with its constructor.** `#[component] fn Checkbox` gives
  `nsh_base::checkbox()`: one setter per prop, named as the field
  (`.checked(..)`, `.indicator_class(..)`), which takes a value or a
  `Reactive` (so `props::boolean`, `props::string` and `props::number`
  feed it straight from Python), a slot setter that takes an element
  (`.indicator(..)`), `.child(..)` for the children, and one listener per
  event (`.on_change(|value: &bool| ..)`). Read the component's file in
  `nsh-base-0.5.0/src/` for its props and events; nsh-engine's
  `tests/engine/rust_styles.rs` styles a switch and a checkbox from Rust.
- **The component has no look.** nsh-base owns the behaviour (presses,
  keys, the disabled state, the role and value for screen readers) and
  nothing else. Python gives each part its look as props
  (`indicator_class`, `track_class`, `thumb_class`), with theme tokens.
  `checked:`, `indeterminate:` and `disabled:` classes on a part follow
  the component's state; on the parts' *children* (the check mark, a
  label) they don't, so Python binds those to the state itself (the mark
  is a `text` bound to `checked`).
- **The root takes no classes (NSH 0.3.0).** `app_class` on a component
  element is dropped: only typed styles (`.flex_row()`) and inline styles
  reach the component's root. So the builder gives the root its layout
  with typed styles (the box, then the label, in a row), and the
  caller's `class_` goes on a `view` around the component
  (`props::with_class`): margins, padding, sizes and the like work, the
  root's own layout doesn't change.
- **The root takes no `test_id`.** A component element isn't
  `Interactive`, which is where `test_id` lives. `props::test_probe` adds
  an empty child over the whole component (`absolute inset-0`, touches
  pass through) that carries the id. nsh-testing's `press("id:..")` finds
  it and presses the nearest view around it that hears presses: the
  component's root. Add the probe last among the children.
- **Two-way binding is Python's.** The component reports the value a
  press asks for (`on_change(True)`) and shows the value it is given.
  `primitives/_toggle.py` turns what the caller passed into both: a
  signal is two-way (the handler sets it, then calls `on_change`), a
  callable is one-way and read-only (the handler only calls
  `on_change`), and a bool is the first value of a signal the toggle
  makes for itself, so `nsh.checkbox("Remember me", checked=True)` still
  toggles.
