//! `radio_group`: nsh-base's `RadioGroup` of `Radio`s (`nsh.radio_group`).
//!
//! Props: `value` (a string or `None`, or a callable), `options` (a list of
//! strings or a callable), `disabled` (a bool or a callable: every radio),
//! `on_change` (called with the chosen string), `radio_class` /
//! `indicator_class` / `dot_class` / `label_class` (each radio's look),
//! plus `class_` (on the group) and `test_id` (`props::test_probe`).
//!
//! nsh-base owns presses, arrow keys and the radiogroup role; the look and
//! the two-way binding are Python's. The group builds one radio per option.

use std::rc::Rc;

use nsh_core::{element::Reactive, prelude::*};
use pyo3::{prelude::*, types::PyDict};

use crate::{bridge, props};

pub(super) fn build(
    _py: Python<'_>,
    props: &Bound<'_, PyDict>,
    _children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let value = match props::get(props, "value")? {
        Some(v) => value_binding(&v)?,
        None => Reactive::Static(None),
    };
    let disabled = match props::get(props, "disabled")? {
        Some(d) => props::boolean(&d)?,
        None => Reactive::Static(false),
    };
    let radio_class = props::optional_string(props, "radio_class")?;
    let indicator_class = props::optional_string(props, "indicator_class")?;
    let dot_class = props::optional_string(props, "dot_class")?;
    let label_class = props::optional_string(props, "label_class")?;
    let on_change = props::get(props, "on_change")?.map(|h| Rc::new(h.unbind()));

    let options = match props::get(props, "options")? {
        Some(options) => options_binding(&options)?,
        None => Reactive::Static(Vec::new()),
    };

    let radios = each(
        options,
        |label| label.clone(),
        move |item, _index| {
            let label = item.get();
            let for_checked = label.clone();
            let for_change = label.clone();
            let value = value.clone();
            let disabled = disabled.clone();
            let on_change = on_change.clone();
            let indicator = view()
                .app_class(indicator_class.clone())
                .child(view().app_class(dot_class.clone()));
            nsh_base::radio()
                .checked(move || value.get().as_deref() == Some(for_checked.as_str()))
                .disabled(disabled)
                .app_class(radio_class.clone())
                .on_change(move |_: &bool| {
                    if let Some(handler) = on_change.as_ref() {
                        let chosen = for_change.clone();
                        bridge::call(|py| handler.call1(py, (chosen.as_ref(),)).map(drop));
                    }
                })
                .child(indicator)
                .child(text(label).app_class(label_class.clone()))
        },
    );

    let mut el = nsh_base::radio_group();
    if let Some(class) = props::get(props, "class_")? {
        el = el.app_class(props::string(&class)?.map(Some));
    }
    el = el.child(radios);
    if let Some(probe) = props::test_probe(props)? {
        el = el.child(probe);
    }
    Ok(el.into_element())
}

fn options_list(value: &Bound<'_, PyAny>) -> PyResult<Vec<SharedString>> {
    Ok(value
        .extract::<Vec<String>>()?
        .into_iter()
        .map(Into::into)
        .collect())
}

fn options_binding(value: &Bound<'_, PyAny>) -> PyResult<Reactive<Vec<SharedString>>> {
    if value.is_callable() {
        let f = value.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| options_list(&f.bind(py).call0()?)).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(options_list(value)?))
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
