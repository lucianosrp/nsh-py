//! `switch`: nsh-base's `Switch` (`nsh.switch`).
//!
//! Props: `checked` and `disabled` (a bool or a callable), `on_change`
//! (called with the value a press asks for, the opposite of `checked`),
//! `track_class` and `thumb_class` (the parts' classes; `checked:` and
//! `disabled:` follow the switch, `checked:translate-x-4` moves the
//! thumb), plus `class_` (on a view around it: `props::with_class`) and
//! `test_id` (`props::test_probe`). The children (a label) come after the
//! track, in a row.
//!
//! nsh-base owns the behaviour (presses, keys, the switch role and value);
//! the look and the two-way binding are Python's.

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
    let mut el = nsh_base::switch().flex_row().items_center();
    if let Some(checked) = props::get(props, "checked")? {
        el = el.checked(props::boolean(&checked)?);
    }
    if let Some(disabled) = props::get(props, "disabled")? {
        el = el.disabled(props::boolean(&disabled)?);
    }
    el = el
        .track_class(props::optional_string(props, "track_class")?)
        .thumb_class(props::optional_string(props, "thumb_class")?);
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
