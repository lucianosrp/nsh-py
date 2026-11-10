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

/// A bool prop: fixed, or bound to a callable (its result's truthiness).
pub(crate) fn boolean(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<bool>> {
    if obj.is_callable() {
        let f = obj.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| f.bind(py).call0()?.is_truthy()).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(obj.is_truthy()?))
    }
}

/// A number prop: fixed, or bound to a callable (its result as a float).
/// A callable that raises (logged) or returns `None` is `0.0`.
pub(crate) fn number(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<f32>> {
    fn of(value: &Bound<'_, PyAny>) -> PyResult<f32> {
        if value.is_none() {
            Ok(0.0)
        } else {
            value.extract::<f32>()
        }
    }
    if obj.is_callable() {
        let f = obj.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| of(&f.bind(py).call0()?)).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(of(obj)?))
    }
}

/// An optional string prop (the classes of a component's part): `None`
/// when unset.
pub(crate) fn optional_string(
    props: &Bound<'_, PyDict>,
    name: &str,
) -> PyResult<Reactive<Option<SharedString>>> {
    Ok(match get(props, name)? {
        Some(value) => string(&value)?.map(Some),
        None => Reactive::Static(None),
    })
}

/// An nsh-base component with `class_`: in a view that takes the classes,
/// when set.
///
/// NSH 0.3.0 drops `app_class` on a component element (only typed styles
/// and inline styles reach the component's root), so the classes go on a
/// view around it: sizes, margins and the like work; the root's own layout
/// is the builder's (typed styles), and its parts' look comes in props
/// (`indicator_class`, `track_class`, ...). See [`test_probe`] for
/// `test_id`.
pub(crate) fn with_class(el: impl IntoElement, props: &Bound<'_, PyDict>) -> PyResult<AnyElement> {
    Ok(match get(props, "class_")? {
        Some(class) => view()
            .app_class(string(&class)?.map(Some))
            .child(el)
            .into_element(),
        None => el.into_element(),
    })
}

/// The child that carries `test_id` for an nsh-base component, if set.
///
/// A component's root can't take a test id (that's [`Interactive`]'s), so
/// this is an empty view over the whole component (`absolute inset-0`)
/// that lets touches through: `id:` selectors find it, and a press on it
/// goes to the nearest view around it that hears presses, the component's
/// root. Put it among the component's children.
pub(crate) fn test_probe(props: &Bound<'_, PyDict>) -> PyResult<Option<AnyElement>> {
    let Some(id) = get(props, "test_id")? else {
        return Ok(None);
    };
    let probe = view()
        .app_class(Some(SharedString::from("absolute inset-0")))
        .pointer_events(PointerEvents::None)
        .test_id(&id.extract::<String>()?);
    Ok(Some(probe.into_element()))
}

/// A listener calling the Python `handler` with a bool (the value a
/// checkbox or switch press asks for). It must be `'static` but not
/// `Send`, so it can hold the `Py<PyAny>`.
pub(crate) fn with_bool(handler: Py<PyAny>) -> impl Fn(&bool) + 'static {
    move |value: &bool| {
        bridge::call(|py| handler.call1(py, (*value,)).map(drop));
    }
}

/// An unsigned int prop: fixed, or bound to a callable. Bools are rejected
/// (`True` is an `int` in Python). A bound call that fails is `0`.
pub(crate) fn u32(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<u32>> {
    if obj.is_callable() {
        let f = obj.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| extract_u32(&f.bind(py).call0()?)).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(extract_u32(obj)?))
    }
}

fn extract_u32(obj: &Bound<'_, PyAny>) -> PyResult<u32> {
    if obj.is_instance_of::<pyo3::types::PyBool>() {
        return Err(PyValueError::new_err(format!(
            "expected an int, got bool ({})",
            if obj.is_truthy()? { "True" } else { "False" }
        )));
    }
    obj.extract::<u32>().map_err(|_| {
        PyValueError::new_err(format!(
            "expected an int in 0..={}, got {}",
            u32::MAX,
            obj.repr()
                .map(|r| r.to_string())
                .unwrap_or_else(|_| "?".into())
        ))
    })
}
