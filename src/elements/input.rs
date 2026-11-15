//! `input`: a text field (`nsh.input`).
//!
//! Props: `value` (a string is the first text, which the user then edits
//! (NSH's `default_value`); a callable is the text itself, controlled
//! (NSH's `value`): the field shows what it returns, again whenever the
//! signals it read change), `placeholder` (a string or a callable),
//! `disabled` (a bool or a callable: no edits, `disabled:` styles),
//! `readonly` (a bool or a callable: no edits, ordinary look), `masked`
//! (hide characters; passwords), `max_length` (an int or a callable),
//! `multiline` (a text area: return inserts a line), `on_change` and
//! `on_submit` (called with the text), plus the common props (`class_`,
//! `test_id`).
//!
//! Two-way binding is Python's job (`nsh.input` wires a signal's `set` to
//! `on_change`): this builder only passes the text to the handler.

use nsh_core::{
    element::{Reactive, input},
    prelude::*,
};
use pyo3::{prelude::*, types::PyDict};

use crate::{bridge, props};

pub(super) fn build(
    _py: Python<'_>,
    props: &Bound<'_, PyDict>,
    _children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = props::common(input(), props)?;
    if let Some(value) = props::get(props, "value")? {
        el = if value.is_callable() {
            el.value(text_binding(&value))
        } else {
            el.default_value(value.str()?.to_string())
        };
    }
    if let Some(placeholder) = props::get(props, "placeholder")? {
        el = el.placeholder(props::string(&placeholder)?.map(|s| s.to_string()));
    }
    el = disabled_and_readonly(el, props)?;
    if let Some(masked) = props::get(props, "masked")? {
        el = el.masked(props::boolean(&masked)?);
    }
    if let Some(max_length) = props::get(props, "max_length")? {
        el = el.max_length(props::u32(&max_length)?);
    }
    if let Some(multiline) = props::get(props, "multiline")? {
        el = el.multiline(props::boolean(&multiline)?);
    }
    if let Some(handler) = props::get(props, "on_change")? {
        el = el.on_change(with_text(handler.unbind()));
    }
    if let Some(handler) = props::get(props, "on_submit")? {
        el = el.on_submit(with_text(handler.unbind()));
    }
    Ok(el.into_element())
}

/// NSH's `disabled` is the accessibility state and the `disabled:` style
/// variant; only `readonly` stops edits. A disabled field is also
/// readonly, so it cannot be typed in; a readonly field keeps its look.
fn disabled_and_readonly(el: Input, props: &Bound<'_, PyDict>) -> PyResult<Input> {
    let disabled = match props::get(props, "disabled")? {
        Some(d) => Some(props::boolean(&d)?),
        None => None,
    };
    let readonly = match props::get(props, "readonly")? {
        Some(r) => Some(props::boolean(&r)?),
        None => None,
    };
    match (disabled, readonly) {
        (None, None) => Ok(el),
        (Some(disabled), None) => Ok(el.disabled(disabled.clone()).readonly(disabled)),
        (None, Some(readonly)) => Ok(el.readonly(readonly)),
        (Some(disabled), Some(readonly)) => Ok(el
            .disabled(disabled.clone())
            .readonly(or_bool(disabled, readonly))),
    }
}

fn or_bool(a: Reactive<bool>, b: Reactive<bool>) -> Reactive<bool> {
    match (a, b) {
        (Reactive::Static(true), _) | (_, Reactive::Static(true)) => Reactive::Static(true),
        (Reactive::Static(false), other) | (other, Reactive::Static(false)) => other,
        (Reactive::Bound(a), Reactive::Bound(b)) => {
            Reactive::Bound(std::rc::Rc::new(move || a() || b()))
        }
    }
}

/// The text a callable returns, read in a binding. `None` is empty, and a
/// callable that raises (logged) is empty too.
fn text_binding(f: &Bound<'_, PyAny>) -> Reactive<String> {
    let f = f.clone().unbind();
    Reactive::Bound(std::rc::Rc::new(move || {
        bridge::call(|py| {
            let value = f.bind(py).call0()?;
            Ok(if value.is_none() {
                String::new()
            } else {
                value.str()?.to_string()
            })
        })
        .unwrap_or_default()
    }))
}

/// A listener calling the Python `handler` with the text. It must be
/// `'static` but not `Send`, so it can hold the `Py<PyAny>`.
fn with_text(handler: Py<PyAny>) -> impl Fn(&str) + 'static {
    move |text: &str| {
        bridge::call(|py| handler.call1(py, (text,)).map(drop));
    }
}
