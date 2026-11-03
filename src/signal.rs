//! What makes `nsh.signal` reactive: an NSH signal with no value of its
//! own (a trigger) that the Python signal reads to subscribe whatever is
//! running and writes to notify it. The value stays in Python; NSH's graph
//! decides what runs again. See `docs/architecture.md`.

use std::cell::Cell;

use nsh_core::{element::create_root, prelude::*};
use pyo3::prelude::*;

use crate::bridge;

/// An NSH `Signal<()>` that notifies on every write, made on first use
/// inside the engine under an owner of its own. A `Cell`, not `&mut self`:
/// reading the signal can run bindings that read it again (re-entrant).
#[pyclass(unsendable, module = "nsh._core")]
pub(crate) struct Trigger {
    made: Cell<Option<(Owner, Signal<()>)>>,
}

#[pymethods]
impl Trigger {
    #[new]
    fn new() -> Self {
        Trigger {
            made: Cell::new(None),
        }
    }

    /// Subscribes the running computation (a binding, a region). Does
    /// nothing outside the engine: there is nothing to subscribe.
    fn track(&self) {
        if !bridge::in_engine() {
            return;
        }
        let signal = match self.made.get() {
            Some((owner, signal)) if owner.is_live() => signal,
            _ => {
                // Its own root: the binding that first read it must not
                // dispose it when it runs again.
                let made = create_root(|| signal_with((), SignalEquals::Never));
                self.made.set(Some(made));
                made.1
            }
        };
        signal.try_get();
    }

    /// Runs again what read it. Returns false if it could not: called
    /// outside the engine while something is subscribed.
    fn notify(&self) -> bool {
        let Some((_, signal)) = self.made.get() else {
            // Never read inside the engine: nothing to notify.
            return true;
        };
        if !bridge::in_engine() {
            return false;
        }
        signal.try_set(());
        true
    }
}

impl Drop for Trigger {
    fn drop(&mut self) {
        // The graph can only be touched while the engine runs Python; a
        // trigger dropped elsewhere leaks one empty slot until the app ends.
        if let Some((owner, _)) = self.made.take()
            && bridge::in_engine()
        {
            owner.dispose();
        }
    }
}

/// Whether Python code running now was called by the engine.
#[pyfunction]
pub(crate) fn in_engine() -> bool {
    bridge::in_engine()
}
