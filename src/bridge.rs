//! Calling Python from the engine thread.
//!
//! Every call into Python from NSH (a component's view, a binding, a
//! listener) goes through [`call`]: it attaches to the interpreter, marks
//! the thread as inside the engine (so `nsh.signal` can use NSH's reactive
//! graph) and turns a Python exception into a log record instead of a
//! crash.

use std::cell::Cell;

use pyo3::{prelude::*, sync::PyOnceLock, types::PyModule};

thread_local! {
    /// How deep this thread is in calls from the engine into Python.
    static ENGINE_DEPTH: Cell<u32> = const { Cell::new(0) };
}

/// Whether Python code running now was called by the engine: NSH's
/// reactive graph is entered and can be used.
pub(crate) fn in_engine() -> bool {
    ENGINE_DEPTH.with(Cell::get) > 0
}

/// Runs `f` with the GIL, marked as inside the engine. A Python exception
/// it returns is logged (`nsh` logger) and becomes `None`.
pub(crate) fn call<R>(f: impl FnOnce(Python<'_>) -> PyResult<R>) -> Option<R> {
    struct Leave;
    impl Drop for Leave {
        fn drop(&mut self) {
            ENGINE_DEPTH.with(|d| d.set(d.get() - 1));
        }
    }
    Python::attach(|py| {
        ENGINE_DEPTH.with(|d| d.set(d.get() + 1));
        let _leave = Leave;
        match f(py) {
            Ok(value) => Some(value),
            Err(err) => {
                report(py, err);
                None
            }
        }
    })
}

/// Logs a Python exception raised by app code: through
/// `nsh._runtime.report_exception`, or printed if that fails too.
pub(crate) fn report(py: Python<'_>, err: PyErr) {
    static REPORT: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
    let reporter = REPORT.get_or_try_init(py, || {
        PyModule::import(py, "nsh._runtime")
            .and_then(|m| m.getattr("report_exception"))
            .map(Bound::unbind)
    });
    let reported = reporter.and_then(|r| r.call1(py, (err.value(py),)).map(drop));
    if let Err(failed) = reported {
        err.print(py);
        failed.print(py);
    }
}
