//! Props shared by many element kinds, and helpers for kinds' own props.
//!
//! A prop is a key of the element's `props` dict. A callable value is a
//! binding: NSH calls it again when the signals it read change.

use std::rc::Rc;

use nsh_core::{element::Reactive, prelude::*};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict};

use crate::bridge;

/// The props every interactive element takes: `class_`, `on_press`,
/// `role` and `test_id`.
pub(crate) fn common<E: Interactive + Accessible>(
    mut el: E,
    props: &Bound<'_, PyDict>,
) -> PyResult<E> {
    if let Some(class) = get(props, "class_")? {
        el = el.app_class(string(&class)?.map(Some));
    }
    if let Some(handler) = get(props, "on_press")? {
        let handler = handler.unbind();
        el = el.on_press(move || {
            bridge::call(|py| handler.call0(py).map(drop));
        });
    }
    if let Some(role) = get(props, "role")? {
        el = el.role(match role.extract::<String>()?.as_str() {
            "button" => AccessibilityRole::Button,
            other => return Err(PyValueError::new_err(format!("unknown role {other:?}"))),
        });
    }
    if let Some(id) = get(props, "test_id")? {
        el = el.test_id(&id.extract::<String>()?);
    }
    Ok(el)
}

/// Prop `name`, if set and not `None`.
pub(crate) fn get<'py>(
    props: &Bound<'py, PyDict>,
    name: &str,
) -> PyResult<Option<Bound<'py, PyAny>>> {
    Ok(props.get_item(name)?.filter(|v| !v.is_none()))
}

/// A string prop: fixed, or bound to a callable (its result's `str()`).
pub(crate) fn string(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<SharedString>> {
    if obj.is_callable() {
        let f = obj.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| Ok(f.bind(py).call0()?.str()?.to_string()))
                .unwrap_or_default()
                .into()
        })))
    } else {
        Ok(Reactive::Static(obj.str()?.to_string().into()))
    }
}
