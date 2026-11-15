//! `select`: nsh-base owns the dropdown, focus, keyboard and accessibility.
//! Python owns the trigger's content and look, and wires two-way signals.

use std::rc::Rc;

use nsh_base::{SelectItem, SelectValue};
use nsh_core::{element::Reactive, prelude::*};
use pyo3::{prelude::*, types::PyDict};

use crate::{bridge, props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut trigger = props::common(view(), props)?;
    for child in tree::children(py, children)? {
        trigger = trigger.child(child);
    }
    let mut el = nsh_base::select().trigger(trigger);
    if let Some(options) = props::get(props, "options")? {
        el = el.items(items_binding(&options)?);
    }
    if let Some(value) = props::get(props, "value")? {
        el = el.value(value_binding(&value)?.map(SelectValue::from));
    }
    if let Some(placeholder) = props::get(props, "placeholder")? {
        el = el.placeholder(props::string(&placeholder)?.map(Some));
    }
    if let Some(disabled) = props::get(props, "disabled")? {
        el = el.disabled(props::boolean(&disabled)?);
    }
    if let Some(label) = props::get(props, "accessibility_label")? {
        el = el.accessibility_label(props::string(&label)?.map(Some));
    }
    el = el
        .popup_class(props::optional_string(props, "popup_class")?)
        .list_class(props::optional_string(props, "list_class")?)
        .item_class(props::optional_string(props, "item_class")?);
    if let Some(handler) = props::get(props, "on_change")? {
        let handler = handler.unbind();
        el = el.on_change(move |value: &Option<SharedString>| {
            bridge::call(|py| handler.call1(py, (value.as_deref(),)).map(drop));
        });
    }
    Ok(el.into_element())
}

fn items(value: &Bound<'_, PyAny>) -> PyResult<Vec<SelectItem>> {
    Ok(value
        .extract::<Vec<String>>()?
        .into_iter()
        .map(|s| SelectItem::new(s.clone(), s))
        .collect())
}

fn items_binding(value: &Bound<'_, PyAny>) -> PyResult<Reactive<Vec<SelectItem>>> {
    if value.is_callable() {
        let f = value.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| items(&f.bind(py).call0()?)).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(items(value)?))
    }
}

fn selected(value: &Bound<'_, PyAny>) -> PyResult<Option<SharedString>> {
    Ok(value.extract::<Option<String>>()?.map(Into::into))
}

fn value_binding(value: &Bound<'_, PyAny>) -> PyResult<Reactive<Option<SharedString>>> {
    if value.is_callable() {
        let f = value.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| selected(&f.bind(py).call0()?)).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(selected(value)?))
    }
}
