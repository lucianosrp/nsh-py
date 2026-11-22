//! `slider`: nsh-base's `Slider` (`nsh.slider`).
//!
//! Props: `value` (a number is the first value, which the user then edits
//! (NSH's `default_value`); a callable is the value itself, controlled
//! (NSH's `value`)), `min` / `max` / `step` (numbers, defaults 0 / 100 /
//! 1), `disabled` (a bool or a callable), `on_change` (called with the
//! number a drag or key asks for), `track_class` / `indicator_class` /
//! `range_class` / `thumb_class` (the parts' classes),
//! `accessibility_label`, plus `class_` (on a view around it:
//! `props::with_class`) and `test_id` (`props::test_probe`). The children
//! (a label) come under the track.
//!
//! nsh-base owns the behaviour (drags, keys, the adjustable role); the
//! look and the two-way binding are Python's.

use nsh_base::{SliderValue, slider};
use nsh_core::{element::Reactive, prelude::*};
use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict};

use crate::{bridge, props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = slider();
    if let Some(value) = props::get(props, "value")? {
        el = if value.is_callable() {
            el.value(value_binding(&value))
        } else {
            el.default_value(float(&value)?)
        };
    }
    if let Some(min) = props::get(props, "min")? {
        el = el.min(float(&min)?);
    }
    if let Some(max) = props::get(props, "max")? {
        el = el.max(float(&max)?);
    }
    if let Some(step) = props::get(props, "step")? {
        el = el.step(float(&step)?);
    }
    if let Some(disabled) = props::get(props, "disabled")? {
        el = el.disabled(props::boolean(&disabled)?);
    }
    if let Some(label) = props::get(props, "accessibility_label")? {
        el = el.accessibility_label(props::string(&label)?.map(Some));
    }
    el = el
        .track_class(props::optional_string(props, "track_class")?)
        .indicator_class(props::optional_string(props, "indicator_class")?)
        .range_class(props::optional_string(props, "range_class")?)
        .thumb_class(props::optional_string(props, "thumb_class")?);
    if let Some(handler) = props::get(props, "on_change")? {
        el = el.on_change(with_value(handler.unbind()));
    }
    for child in tree::children(py, children)? {
        el = el.child(child);
    }
    if let Some(probe) = props::test_probe(props)? {
        el = el.child(probe);
    }
    props::with_class(el, props)
}

/// A number from Python: rejects bools (`True` is an `int`).
fn float(obj: &Bound<'_, PyAny>) -> PyResult<f64> {
    if obj.is_instance_of::<pyo3::types::PyBool>() {
        return Err(PyValueError::new_err(format!(
            "expected a number, got bool ({})",
            if obj.is_truthy()? { "True" } else { "False" }
        )));
    }
    obj.extract::<f64>().map_err(|_| {
        PyValueError::new_err(format!(
            "expected a number, got {}",
            obj.repr()
                .map(|r| r.to_string())
                .unwrap_or_else(|_| "?".into())
        ))
    })
}

/// The value a callable returns, as a controlled slider value. `None` or a
/// raise (logged) is `0`.
fn value_binding(f: &Bound<'_, PyAny>) -> Reactive<Option<SliderValue>> {
    let f = f.clone().unbind();
    Reactive::Bound(std::rc::Rc::new(move || {
        let v = bridge::call(|py| {
            let value = f.bind(py).call0()?;
            if value.is_none() {
                Ok(0.0)
            } else {
                float(&value)
            }
        })
        .unwrap_or_default();
        Some(SliderValue::from(v))
    }))
}

/// A listener calling the Python `handler` with the slider's number (a
/// single value, or a range's start). It must be `'static` but not `Send`,
/// so it can hold the `Py<PyAny>`.
fn with_value(handler: Py<PyAny>) -> impl Fn(&SliderValue) + 'static {
    move |value: &SliderValue| {
        let n = value.start();
        bridge::call(|py| handler.call1(py, (n,)).map(drop));
    }
}
