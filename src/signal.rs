//! What makes `nsh.signal` reactive: an NSH signal with no value of its
//! own (a trigger) that the Python signal reads to subscribe whatever is
//! running and writes to notify it. The value stays in Python; NSH's graph
//! decides what runs again. See `docs/architecture.md`.

use std::{
    sync::Mutex,
    thread::{self, ThreadId},
};

use nsh_core::{element::create_root, prelude::*};
use pyo3::prelude::*;

use crate::bridge;

/// The NSH signal behind a trigger, and the engine thread whose graph holds
/// it: ids from one engine mean nothing in another's (a signal that outlives
/// a headless app in tests).
#[derive(Clone, Copy)]
struct Made {
    thread: ThreadId,
    owner: Owner,
    signal: Signal<()>,
}

/// An NSH `Signal<()>` that notifies on every write, made on first use
/// inside the engine under an owner of its own.
///
/// Not `unsendable`: Python may free it on any thread (the main thread
/// once an app's engine stops), and its handles are plain ids. The lock is
/// held only to copy them out: reading the signal can run bindings that
/// read it again (re-entrant).
#[pyclass(module = "nsh._core")]
pub(crate) struct Trigger {
    made: Mutex<Option<Made>>,
}

impl Trigger {
    fn made(&self) -> Option<Made> {
        *self.made.lock().unwrap_or_else(|e| e.into_inner())
    }

    /// Its signal in this engine's graph, if it has a live one.
    fn here(&self) -> Option<Signal<()>> {
        self.made()
            .filter(|m| m.thread == thread::current().id() && m.owner.is_live())
            .map(|m| m.signal)
    }
}

#[pymethods]
impl Trigger {
    #[new]
    fn new() -> Self {
        Trigger {
            made: Mutex::new(None),
        }
    }

    /// Subscribes the running computation (a binding, a region). Does
    /// nothing outside the engine: there is nothing to subscribe.
    fn track(&self) {
        if !bridge::in_engine() {
            return;
        }
        let signal = match self.here() {
            Some(signal) => signal,
            None => {
                // Its own root: the binding that first read it must not
                // dispose it when it runs again.
                let (owner, signal) = create_root(|| signal_with((), SignalEquals::Never));
                *self.made.lock().unwrap_or_else(|e| e.into_inner()) = Some(Made {
                    thread: thread::current().id(),
                    owner,
                    signal,
                });
                signal
            }
        };
        signal.try_get();
    }

    /// Runs again what read it. Returns false if it could not: called
    /// outside the engine while something is subscribed. Writers on other
    /// threads post the notify to the engine (`nsh.call_soon`), which is what
    /// `nsh.signal` does.
    fn notify(&self) -> bool {
        if self.made().is_none() {
            // Never read inside the engine: nothing to notify.
            return true;
        }
        if !bridge::in_engine() {
            return false;
        }
        if let Some(signal) = self.here() {
            signal.try_set(());
        }
        true
    }
}

impl Drop for Trigger {
    fn drop(&mut self) {
        // The graph can only be touched on its engine thread. Dropped
        // elsewhere, the disposal is posted there; with no app running the
        // engine is gone and its graph with it.
        let made = self
            .made
            .get_mut()
            .unwrap_or_else(|e| e.into_inner())
            .take();
        let Some(made) = made else {
            return;
        };
        if bridge::in_engine() && made.thread == thread::current().id() {
            made.owner.dispose();
        } else {
            let _ = crate::queue::post(Box::new(move || {
                if made.thread == thread::current().id() && made.owner.is_live() {
                    made.owner.dispose();
                }
            }));
        }
    }
}

/// Notifies `triggers` together: what read several of them (a binding that
/// reads a computed and the signal it reads) runs once, not once for each.
/// Does nothing outside the engine.
#[pyfunction]
pub(crate) fn notify_all(triggers: Vec<PyRef<'_, Trigger>>) {
    if !bridge::in_engine() {
        return;
    }
    batch(|| {
        for trigger in &triggers {
            trigger.notify();
        }
    });
}

/// Whether Python code running now was called by the engine.
#[pyfunction]
pub(crate) fn in_engine() -> bool {
    bridge::in_engine()
}
