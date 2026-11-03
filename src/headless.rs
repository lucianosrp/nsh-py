//! A headless app for tests (`nsh.testing`): nsh-testing's driver runs the
//! engine with no window and no display; the test presses elements and
//! reads the texts shown.

use std::{sync::Mutex, time::Duration};

use nsh_core::geometry::{Points, Size};
use nsh_engine::EngineConfig;
use nsh_testing::Headless as Driver;
use pyo3::{
    exceptions::{PyRuntimeError, PyTimeoutError},
    prelude::*,
};

/// A running headless app. Its methods release the GIL: the engine thread
/// calls Python (views, bindings, handlers) while they wait.
#[pyclass(module = "nsh._core")]
pub(crate) struct Headless {
    driver: Mutex<Option<Driver>>,
}

impl Headless {
    fn with<R>(
        &self,
        py: Python<'_>,
        f: impl FnOnce(&mut Driver) -> PyResult<R> + Send,
    ) -> PyResult<R>
    where
        R: Send,
    {
        py.detach(|| {
            let mut driver = self.driver.lock().unwrap_or_else(|e| e.into_inner());
            match driver.as_mut() {
                Some(driver) => f(driver),
                None => Err(PyRuntimeError::new_err("the app is closed")),
            }
        })
    }
}

#[pymethods]
impl Headless {
    /// Starts `root` (as `nsh.run` takes it) and waits for its first frame.
    #[new]
    #[pyo3(signature = (root=None, *, size=(390.0, 844.0)))]
    fn new(py: Python<'_>, root: Option<Py<PyAny>>, size: (f32, f32)) -> PyResult<Self> {
        crate::app::set_root(root);
        let driver = py.detach(|| {
            let mut config = EngineConfig::new(crate::app::app_root());
            config.ui_sets = vec![nsh_base::registry()];
            config.viewport = Size::new(Points(size.0), Points(size.1));
            let mut driver = Driver::start(config)
                .map_err(|e| PyRuntimeError::new_err(format!("could not start: {e}")))?;
            driver.first_render().map_err(PyTimeoutError::new_err)?;
            Ok::<_, PyErr>(driver)
        })?;
        Ok(Headless {
            driver: Mutex::new(Some(driver)),
        })
    }

    /// Presses what `selector` finds (`"+1"`, `"id:inc"`, `"text:+1"`) and
    /// waits until the app settles.
    fn press(&self, py: Python<'_>, selector: String) -> PyResult<()> {
        self.with(py, |d| {
            d.press(&selector).map_err(PyRuntimeError::new_err)?;
            d.settle();
            Ok(())
        })
    }

    /// Waits until `selector` shows (default 5 s).
    #[pyo3(signature = (selector, timeout=5.0))]
    fn wait_for(&self, py: Python<'_>, selector: String, timeout: f64) -> PyResult<()> {
        self.with(py, |d| {
            d.wait_for_within(&selector, Duration::from_secs_f64(timeout))
                .map_err(PyTimeoutError::new_err)
        })
    }

    /// The texts shown, in order.
    fn texts(&self, py: Python<'_>) -> PyResult<Vec<String>> {
        self.with(py, |d| {
            d.catch_up();
            Ok(d.screen().texts().into_iter().map(str::to_owned).collect())
        })
    }

    /// Whether `text` shows.
    fn shows(&self, py: Python<'_>, text: String) -> PyResult<bool> {
        self.with(py, |d| {
            d.catch_up();
            Ok(d.shows(&text))
        })
    }

    /// Stops the engine (joining its thread).
    fn close(&self, py: Python<'_>) {
        py.detach(|| {
            self.driver.lock().unwrap_or_else(|e| e.into_inner()).take();
        });
    }
}
