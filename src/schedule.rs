//! Work the engine runs for Python: effects and timers.
//!
//! Both are made on the engine thread (`new`/`arm` raise anywhere else;
//! the Python layer posts them through the queue) and owned by the owner
//! running when they're made: a component's effect or timer ends with the
//! component. Their handles are plain ids, so Python may hold and use them
//! on any thread.

use std::{
    sync::{
        Arc, Mutex,
        atomic::{AtomicBool, Ordering},
    },
    thread::{self, ThreadId},
    time::Duration,
};

use nsh_core::{element::create_root, prelude::*};
use pyo3::{exceptions::PyRuntimeError, prelude::*, types::PyTuple};

use crate::{bridge, queue};

fn engine_only(what: &str) -> PyResult<()> {
    if bridge::in_engine() {
        Ok(())
    } else {
        Err(PyRuntimeError::new_err(format!(
            "{what} can only be made on the app's thread (use nsh.call_soon)"
        )))
    }
}

/// An NSH effect running a Python function: now, and again whenever the
/// signals it read change. It lives in an owner of its own, so it can be
/// disposed alone, and the owner that was running when it was made disposes
/// it too.
#[pyclass(module = "nsh._core")]
pub(crate) struct Effect {
    made: Mutex<Option<(ThreadId, Owner)>>,
}

#[pymethods]
impl Effect {
    /// Runs `func` now, and again when what it read changes. Only on the
    /// engine thread.
    #[new]
    fn new(func: Py<PyAny>) -> PyResult<Self> {
        engine_only("an effect")?;
        let (owner, ()) = create_root(|| {
            effect(move || {
                bridge::call(|py| func.call0(py).map(drop));
            });
        });
        // The component (or other owner) running now ends the effect too.
        cleanup(move || owner.dispose());
        Ok(Effect {
            made: Mutex::new(Some((thread::current().id(), owner))),
        })
    }

    /// Stops the effect: it never runs again. From another thread this is
    /// posted to the engine. Does nothing twice.
    fn dispose(&self) {
        let made = self.made.lock().unwrap_or_else(|e| e.into_inner()).take();
        let Some((thread, owner)) = made else {
            return;
        };
        let dispose = move || {
            if thread::current().id() == thread && owner.is_live() {
                owner.dispose();
            }
        };
        if bridge::in_engine() {
            dispose();
        } else {
            // Without an app the engine is gone, and so is the effect.
            let _ = queue::post(Box::new(dispose));
        }
    }
}

/// A timer: `func(*args)` after `seconds`, or every `seconds`. Made
/// unarmed; [`arm`](Timer::arm) starts it on the engine. Cancelling is
/// a flag, so it works from any thread: the function isn't called again
/// and the engine's task ends the next time it wakes.
#[pyclass(module = "nsh._core")]
pub(crate) struct Timer {
    func: Py<PyAny>,
    args: Py<PyTuple>,
    period: Duration,
    repeat: bool,
    cancelled: Arc<AtomicBool>,
}

#[pymethods]
impl Timer {
    #[new]
    fn new(func: Py<PyAny>, args: Py<PyTuple>, seconds: f64, repeat: bool) -> PyResult<Self> {
        if !seconds.is_finite() || seconds < 0.0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "seconds must be a number >= 0",
            ));
        }
        // An interval of 0 would spin the engine.
        let seconds = if repeat { seconds.max(0.001) } else { seconds };
        Ok(Timer {
            func,
            args,
            period: Duration::from_secs_f64(seconds),
            repeat,
            cancelled: Arc::new(AtomicBool::new(false)),
        })
    }

    /// Starts the timer, under the owner running now. Only on the engine
    /// thread; does nothing if it was cancelled.
    fn arm(&self, py: Python<'_>) -> PyResult<()> {
        engine_only("a timer")?;
        if self.cancelled.load(Ordering::Acquire) {
            return Ok(());
        }
        let cancelled = self.cancelled.clone();
        let func = self.func.clone_ref(py);
        let args = self.args.clone_ref(py);
        let (period, repeat) = (self.period, self.repeat);
        let fire = move || {
            if !cancelled.load(Ordering::Acquire) {
                bridge::call(|py| func.call1(py, args.bind(py)).map(drop));
            }
        };
        let flag = self.cancelled.clone();
        // The task ends with the owner, like NSH's own timers.
        spawn(async move {
            let mut next = nsh_core::time::now() + period;
            loop {
                timer_until(next).await;
                if flag.load(Ordering::Acquire) {
                    return;
                }
                fire();
                if !repeat {
                    return;
                }
                // Late wakes don't pile up runs.
                next = (next + period).max(nsh_core::time::now());
            }
        });
        Ok(())
    }

    /// Stops the timer: `fn` is never called again. Safe from any thread.
    fn cancel(&self) {
        self.cancelled.store(true, Ordering::Release);
    }

    /// Whether it was cancelled.
    #[getter]
    fn cancelled(&self) -> bool {
        self.cancelled.load(Ordering::Acquire)
    }
}

pub(crate) fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Effect>()?;
    m.add_class::<Timer>()
}
