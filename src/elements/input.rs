//! `input`: a one-line text field (`nsh.input`).
//!
//! Props: `value` (a string is the first text, which the user then edits
//! (NSH's `default_value`); a callable is the text itself, controlled
//! (NSH's `value`): the field shows what it returns, again whenever the
//! signals it read change), `placeholder` (a string or a callable),
//! `disabled` (a bool or a callable: no edits, `disabled:` styles), `on_change` and `on_submit` (called
//! with the text), plus the common props (`class_`, `test_id`).
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
    if let Some(disabled) = props::get(props, "disabled")? {
        // NSH's `disabled` is the accessibility state and the `disabled:`
        // style variant; only `readonly` stops edits.
        let disabled = props::boolean(&disabled)?;
        el = el.disabled(disabled.clone()).readonly(disabled);
    }
    if let Some(handler) = props::get(props, "on_change")? {
        el = el.on_change(with_text(handler.unbind()));
    }
    if let Some(handler) = props::get(props, "on_submit")? {
        el = el.on_submit(with_text(handler.unbind()));
    }
    Ok(el.into_element())
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
