//! `checkbox`: nsh-base's `Checkbox` (`nsh.checkbox`).
//!
//! Props: `checked`, `indeterminate` and `disabled` (a bool or a
//! callable), `on_change` (called with the value a press asks for:
//! `True` from unchecked and from indeterminate, `False` from checked),
//! `indicator_class` (the box's classes; `checked:`, `indeterminate:` and
//! `disabled:` follow the checkbox), `indicator` (an element: the mark in
//! the box), plus `class_` (on a view around it: `props::with_class`) and
//! `test_id` (`props::test_probe`). The children (a label) come after the
//! box, in a row.
//!
//! nsh-base owns the behaviour (presses, keys, the checkbox role and
//! value); the look and the two-way binding are Python's.

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    // The box (track) then the label, in a row: the root can't take
    // classes (see `props::with_class`).
    let mut el = nsh_base::checkbox().flex_row().items_center();
    if let Some(checked) = props::get(props, "checked")? {
        el = el.checked(props::boolean(&checked)?);
    }
    if let Some(indeterminate) = props::get(props, "indeterminate")? {
        el = el.indeterminate(props::boolean(&indeterminate)?);
    }
    if let Some(disabled) = props::get(props, "disabled")? {
        el = el.disabled(props::boolean(&disabled)?);
    }
    el = el.indicator_class(props::optional_string(props, "indicator_class")?);
    if let Some(mark) = props::get(props, "indicator")? {
        el = el.indicator(one(tree::children(py, &mark)?));
    }
    if let Some(handler) = props::get(props, "on_change")? {
        el = el.on_change(props::with_bool(handler.unbind()));
    }
    for child in tree::children(py, children)? {
        el = el.child(child);
    }
    if let Some(probe) = props::test_probe(props)? {
        el = el.child(probe);
    }
    props::with_class(el, props)
}

/// `elements` as one element: itself if there's one, else a view of them.
fn one(mut elements: Vec<AnyElement>) -> AnyElement {
    if elements.len() == 1 {
        return elements.remove(0);
    }
    let mut el = view();
    for child in elements {
        el = el.child(child);
    }
    el.into_element()
}
