//! A headless app for tests (`nsh.testing`): nsh-testing's driver runs the
//! engine with no window and no display; the test presses elements and
//! reads the texts shown.

use std::{sync::Mutex, time::Duration};

use nsh_core::{
    Command, EventKind, EventPayload, NodeId, PayloadValue,
    geometry::{Points, Size},
    platform::{Idiom, Os},
};
use nsh_engine::EngineConfig;
use nsh_testing::Headless as Driver;
use pyo3::{
    exceptions::{PyRuntimeError, PyTimeoutError, PyValueError},
    prelude::*,
    types::{PyBool, PyDict, PyString},
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
    /// `desktop`: it runs as a Linux desktop app, with a main window whose
    /// state `window_state` reports (else NSH's default, a phone).
    #[new]
    #[pyo3(signature = (root=None, *, size=(390.0, 844.0), desktop=false))]
    fn new(
        py: Python<'_>,
        root: Option<Py<PyAny>>,
        size: (f32, f32),
        desktop: bool,
    ) -> PyResult<Self> {
        crate::app::set_root(root);
        crate::queue::begin();
        let driver = py.detach(|| {
            let mut config = EngineConfig::new(crate::app::app_root());
            config.ui_sets = vec![nsh_base::registry()];
            config.viewport = Size::new(Points(size.0), Points(size.1));
            if desktop {
                config.environment.os = Os::Linux;
                config.environment.idiom = Idiom::Desktop;
            }
            let mut driver = Driver::start(config)
                .map_err(|e| PyRuntimeError::new_err(format!("could not start: {e}")))?;
            driver.first_render().map_err(PyTimeoutError::new_err)?;
            Ok::<_, PyErr>(driver)
        });
        let driver = match driver {
            Ok(driver) => driver,
            Err(err) => {
                crate::queue::end();
                return Err(err);
            }
        };
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

    /// Types `text` at the end of the input `selector` finds, key by key,
    /// as a keyboard does (`"\n"` is the return key: it submits), and waits
    /// until the app settles.
    fn type_text(&self, py: Python<'_>, selector: String, text: String) -> PyResult<()> {
        self.with(py, |d| {
            d.type_text(&selector, &text)
                .map_err(PyRuntimeError::new_err)?;
            d.settle();
            Ok(())
        })
    }

    /// Scrolls the scroll view `selector` names by `distance` points along
    /// its axis (negative: back), then waits until the app settles.
    fn scroll(&self, py: Python<'_>, selector: String, distance: f32) -> PyResult<()> {
        self.with(py, |d| {
            d.scroll(&selector, Points(distance))
                .map_err(PyRuntimeError::new_err)?;
            d.settle();
            Ok(())
        })
    }

    /// The text an input holds (`selector` finds the input), or `None` if
    /// no input matches.
    fn value(&self, py: Python<'_>, selector: String) -> PyResult<Option<String>> {
        self.with(py, |d| {
            d.catch_up();
            let value = d.screen().input_text(&selector);
            value
                .map(|v| v.map(str::to_owned))
                .map_err(PyRuntimeError::new_err)
        })
    }

    /// Delivers `event` (its protocol name, `"onLoad"`) with the fields
    /// `data` to the view whose test id is `test_id`, as a platform would,
    /// and waits until the app settles.
    #[pyo3(signature = (test_id, event, data=None))]
    fn dispatch(
        &self,
        py: Python<'_>,
        test_id: String,
        event: String,
        data: Option<Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let kind = EventKind::from_prop(&event)
            .ok_or_else(|| PyValueError::new_err(format!("unknown event {event:?}")))?;
        let mut fields = Vec::new();
        for (key, value) in data.iter().flat_map(|d| d.iter()) {
            let value = if value.is_instance_of::<PyBool>() {
                PayloadValue::Bool(value.extract()?)
            } else if value.is_instance_of::<PyString>() {
                PayloadValue::Str(value.extract()?)
            } else {
                PayloadValue::Number(value.extract()?)
            };
            // A payload's keys are `&'static str`: leaking a test's few
            // field names is the price.
            let key: &'static str = Box::leak(key.extract::<String>()?.into_boxed_str());
            fields.push((key, value));
        }
        self.with(py, |d| {
            d.catch_up();
            let node = node_with_test_id(d, &test_id)?;
            d.engine()
                .control()
                .dispatch_event(node, kind, EventPayload::Map(fields));
            d.settle();
            Ok(())
        })
    }

    /// The seconds of the seeks sent to the video whose test id is
    /// `test_id`, in order.
    fn seeks(&self, py: Python<'_>, test_id: String) -> PyResult<Vec<f64>> {
        self.with(py, |d| {
            d.catch_up();
            let node = node_with_test_id(d, &test_id)?;
            Ok(d.screen()
                .commands()
                .iter()
                .filter_map(|(id, command)| match command {
                    Command::Seek(seconds) if *id == node => Some(*seconds),
                    _ => None,
                })
                .collect())
        })
    }

    /// What the platform reports of window `window_id` (`"main"`): whether
    /// it is visible, minimized and focused; `None` while it is not open.
    #[pyo3(signature = (window_id="main".to_owned()))]
    fn window_state(
        &self,
        py: Python<'_>,
        window_id: String,
    ) -> PyResult<Option<(bool, bool, bool)>> {
        self.with(py, |d| {
            let state = d
                .window_state(&window_id)
                .map_err(PyRuntimeError::new_err)?;
            Ok(state.map(|s| (s.visible, s.minimized, s.focused)))
        })
    }

    /// Stops the engine (joining its thread).
    fn close(&self, py: Python<'_>) {
        py.detach(|| {
            let driver = self.driver.lock().unwrap_or_else(|e| e.into_inner()).take();
            if driver.is_some() {
                drop(driver); // joins the engine thread
                crate::queue::end();
            }
        });
    }
}

/// The view whose test id is `test_id`, written bare or as the selector
/// `id:<test id>` (nsh-testing's selector resolver is private).
fn node_with_test_id(d: &Driver, test_id: &str) -> PyResult<NodeId> {
    let test_id = test_id.strip_prefix("id:").unwrap_or(test_id);
    d.screen()
        .layout_nodes()
        .into_iter()
        .find(|n| n.test_id.as_deref() == Some(test_id))
        .map(|n| n.id)
        .ok_or_else(|| PyRuntimeError::new_err(format!("no view has test id {test_id:?}")))
}

impl Drop for Headless {
    fn drop(&mut self) {
        let driver = self
            .driver
            .get_mut()
            .unwrap_or_else(|e| e.into_inner())
            .take();
        if driver.is_some() {
            // Joining the engine thread: it may be calling Python.
            Python::attach(|py| py.detach(|| drop(driver)));
            crate::queue::end();
        }
    }
}
