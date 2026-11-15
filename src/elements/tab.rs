//! `tab`: nsh-base owns presses, keys, the tab role and selected state.
//! Python owns the look and which tab is selected.

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{bridge, props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = nsh_base::tab();
    if let Some(selected) = props::get(props, "selected")? {
        el = el.selected(props::boolean(&selected)?);
    }
    if let Some(disabled) = props::get(props, "disabled")? {
        el = el.disabled(props::boolean(&disabled)?);
    }
    if let Some(handler) = props::get(props, "on_press")? {
        let handler = handler.unbind();
        el = el.on_press(move |_: &()| {
            bridge::call(|py| handler.call0(py).map(drop));
        });
    }
    if let Some(class) = props::get(props, "class_")? {
        el = el.app_class(props::string(&class)?.map(Some));
    }
    for child in tree::children(py, children)? {
        el = el.child(child);
    }
    if let Some(probe) = props::test_probe(props)? {
        el = el.child(probe);
    }
    Ok(el.into_element())
}
