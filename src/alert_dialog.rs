//! `alert_dialog`: show nsh-base's native alert dialog (`nsh.alert_dialog`).
//!
//! Arguments: `title`, `description`, `actions` as `(id, label, role)`
//! tuples, and an optional `on_result` callback. The callback runs on the
//! engine thread with the chosen action's id, or `None` when dismissed.

use nsh_core::prelude::*;
use pyo3::{
    exceptions::{PyRuntimeError, PyValueError},
    prelude::*,
};

use crate::bridge;

/// Shows an alert and spawns the task that waits for its answer.
#[pyfunction]
#[pyo3(signature = (title, description, actions, on_result=None))]
pub(crate) fn alert_dialog(
    title: String,
    description: Option<String>,
    actions: Vec<(String, String, String)>,
    on_result: Option<Py<PyAny>>,
) -> PyResult<()> {
    if !bridge::in_engine() {
        return Err(PyRuntimeError::new_err(
            "alert_dialog can only be shown from app code (use nsh.call_soon)",
        ));
    }
    if title.is_empty() {
        return Err(PyValueError::new_err(
            "alert_dialog title must be a non-empty string",
        ));
    }
    if actions.is_empty() {
        return Err(PyValueError::new_err(
            "alert_dialog needs at least one action",
        ));
    }
    if actions.len() > 3 {
        return Err(PyValueError::new_err(
            "alert_dialog accepts at most three actions",
        ));
    }

    let mut dialog = nsh_base::alert_dialog().title(title);
    if let Some(description) = description {
        dialog = dialog.description(description);
    }
    for (action_id, label, role) in actions {
        dialog = match role.as_str() {
            "default" => dialog.action(action_id, label),
            "cancel" => dialog.cancel(action_id, label),
            "destructive" => dialog.destructive(action_id, label),
            other => {
                return Err(PyValueError::new_err(format!(
                    "unknown alert_dialog action role {other:?}"
                )));
            }
        };
    }

    let shown = dialog.show();
    spawn(async move {
        match shown.await {
            Ok(result) => {
                let action = result.action.map(|value| value.to_string());
                if let Some(callback) = on_result {
                    let _ = bridge::call(|py| callback.call1(py, (action,)).map(drop));
                }
            }
            Err(error) => {
                let _ = bridge::call(|_py| -> PyResult<()> { Err(PyRuntimeError::new_err(error)) });
            }
        }
    });
    Ok(())
}
