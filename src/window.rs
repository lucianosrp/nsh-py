//! The app and its window: `nsh.quit()` and `nsh.current_window()`.
//!
//! NSH's `quit` and `WindowRef` belong to the engine thread (a `WindowRef`
//! holds `Rc`s). The Python handle is a plain id into a table on that
//! thread, so Python may hold it and call it from any thread: from
//! elsewhere the call is posted to the engine, as `Effect.dispose` does.

use std::{
    cell::RefCell,
    collections::HashMap,
    sync::atomic::{AtomicU64, Ordering},
};

use nsh_core::{
    element::desktop::{self, WindowRef},
    prelude::*,
};
use pyo3::{exceptions::PyRuntimeError, prelude::*};

use crate::{bridge, queue};

thread_local! {
    /// The windows Python holds handles to, on the engine thread.
    static WINDOWS: RefCell<HashMap<u64, WindowRef>> = RefCell::new(HashMap::new());
}

static NEXT_ID: AtomicU64 = AtomicU64::new(1);

/// Runs `job` on the engine thread: now when called there, else posted.
/// With no app running there is nothing to act on, so it is dropped.
fn on_engine(job: impl FnOnce() + Send + 'static) {
    if bridge::in_engine() {
        job();
    } else {
        let _ = queue::post(Box::new(job));
    }
}

/// Quits the app, as the Quit menu item does: its windows close and
/// `nsh.run` returns (on Windows, NSH 0.5.1's `run_app` ends the process
/// instead). Safe from any thread; does nothing with no app.
#[pyfunction]
pub(crate) fn quit() {
    on_engine(desktop::quit);
}

/// The window the calling code renders in. Only on the engine thread,
/// while the app builds its tree: the handle lives as long as the
/// component that made it.
#[pyfunction]
pub(crate) fn current_window() -> PyResult<Window> {
    if !bridge::in_engine() {
        return Err(PyRuntimeError::new_err(
            "nsh.current_window() can only be called while the app builds its tree",
        ));
    }
    let window = desktop::current_window();
    let is_main = window.is_main();
    let name = window.id().to_owned();
    let id = NEXT_ID.fetch_add(1, Ordering::Relaxed);
    WINDOWS.with_borrow_mut(|w| w.insert(id, window));
    cleanup(move || {
        WINDOWS.with_borrow_mut(|w| w.remove(&id));
    });
    Ok(Window { id, name, is_main })
}

/// A handle on one of the app's windows (`nsh.current_window()`). Its
/// methods are safe from any thread; once the component that made it is
/// gone, they do nothing.
#[pyclass(module = "nsh._core", frozen)]
pub(crate) struct Window {
    id: u64,
    name: String,
    is_main: bool,
}

impl Window {
    fn act(&self, f: fn(&WindowRef)) {
        let id = self.id;
        on_engine(move || {
            let window = WINDOWS.with_borrow(|w| w.get(&id).cloned());
            if let Some(window) = window {
                f(&window);
            }
        });
    }
}

#[pymethods]
impl Window {
    /// The window's id: `"main"` for the main window.
    #[getter]
    fn id(&self) -> &str {
        &self.name
    }

    /// Whether it is the main window.
    #[getter]
    fn is_main(&self) -> bool {
        self.is_main
    }

    /// Closes it. Closing the main window ends the app, as when the user
    /// closes it.
    fn close(&self) {
        self.act(WindowRef::close);
    }

    /// Hides it.
    fn hide(&self) {
        self.act(WindowRef::hide);
    }

    /// Shows it, restoring it when minimized.
    fn show(&self) {
        self.act(WindowRef::show);
    }

    /// Shows it, brings it to the front and focuses it.
    fn focus(&self) {
        self.act(WindowRef::focus);
    }

    /// Minimizes it.
    fn minimize(&self) {
        self.act(WindowRef::minimize);
    }

    fn __repr__(&self) -> String {
        format!("<nsh window {:?}>", self.name)
    }
}
