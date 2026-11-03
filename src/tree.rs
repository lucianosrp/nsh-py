//! Python element trees (`nsh.view`, `nsh.text`, ...) as NSH elements.
//!
//! Python builds plain `nsh.Element` objects (`kind`, `props`,
//! `children`); this module turns them into NSH elements on the engine
//! thread. A callable where a value goes (a text's content, a `class_`) is
//! a binding: NSH calls it again when the signals it read change. A
//! callable child is a region made again the same way (`dynamic`).

use std::rc::Rc;

use nsh_core::{element::Reactive, prelude::*};
use pyo3::{
    prelude::*,
    sync::PyOnceLock,
    types::{PyDict, PyList, PyString, PyTuple},
};

use crate::bridge;

/// `nsh._elements.Element`.
fn element_class(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
    static CLASS: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
    CLASS
        .get_or_try_init(py, || {
            Ok::<_, PyErr>(py.import("nsh._elements")?.getattr("Element")?.unbind())
        })
        .map(|c| c.bind(py))
}

/// The elements `obj` stands for, as a child: an `Element`, a string (a
/// text), `None` (nothing), a list or tuple of children, or a callable
/// returning children (a region made again when what it reads changes).
pub(crate) fn children(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Vec<AnyElement>> {
    if obj.is_none() {
        return Ok(Vec::new());
    }
    if obj.is_instance(element_class(py)?)? {
        return Ok(vec![element(py, obj)?]);
    }
    if obj.is_instance_of::<PyString>() {
        return Ok(vec![text(obj.extract::<String>()?).into_element()]);
    }
    if obj.is_instance_of::<PyList>() || obj.is_instance_of::<PyTuple>() {
        let mut out = Vec::new();
        for child in obj.try_iter()? {
            out.extend(children(py, &child?)?);
        }
        return Ok(out);
    }
    if obj.is_callable() {
        let f = obj.clone().unbind();
        return Ok(vec![dynamic(move || {
            bridge::call(|py| children(py, &f.bind(py).call0()?)).unwrap_or_default()
        })]);
    }
    // Anything else shows as its `str()` (numbers, say).
    Ok(vec![text(obj.str()?.to_string()).into_element()])
}

/// One `nsh.Element`.
fn element(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<AnyElement> {
    let kind: String = obj.getattr("kind")?.extract()?;
    let props = obj.getattr("props")?.cast_into::<PyDict>()?;
    let kids = obj.getattr("children")?;
    match kind.as_str() {
        "view" => {
            let mut el = with_props(view(), &props)?;
            for child in children(py, &kids)? {
                el = el.child(child);
            }
            Ok(el.into_element())
        }
        "text" => {
            let content = match props.get_item("content")? {
                Some(c) => string(&c)?,
                None => Reactive::Static(SharedString::default()),
            };
            Ok(with_props(text(content), &props)?.into_element())
        }
        other => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "unknown element kind {other:?}"
        ))),
    }
}

/// The props every element takes: `class_`, `on_press`, `role` and
/// `test_id`.
fn with_props<E: Interactive + Accessible>(mut el: E, props: &Bound<'_, PyDict>) -> PyResult<E> {
    if let Some(class) = props.get_item("class_")?
        && !class.is_none()
    {
        el = el.app_class(string(&class)?.map(Some));
    }
    if let Some(handler) = props.get_item("on_press")?
        && !handler.is_none()
    {
        let handler = handler.unbind();
        el = el.on_press(move || {
            bridge::call(|py| handler.call0(py).map(drop));
        });
    }
    if let Some(role) = props.get_item("role")? {
        match role.extract::<String>()?.as_str() {
            "button" => el = el.role(AccessibilityRole::Button),
            other => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "unknown role {other:?}"
                )));
            }
        }
    }
    if let Some(id) = props.get_item("test_id")? {
        el = el.test_id(&id.extract::<String>()?);
    }
    Ok(el)
}

/// A string prop: fixed, or bound to a callable (its result's `str()`).
fn string(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<SharedString>> {
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
