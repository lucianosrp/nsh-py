//! `scroll`: a scroll view (`nsh.scroll`). Prop `horizontal`: scroll
//! sideways instead of down. NSH has no `overflow-y-auto` on a `view`;
//! this is the element that scrolls.

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = scroll();
    let horizontal = match props::get(props, "horizontal")? {
        Some(h) => h.extract::<bool>()?,
        None => false,
    };
    if horizontal {
        el = el.horizontal();
    }
    let mut el = props::common(el, props)?;
    for child in tree::children(py, children)? {
        el = el.child(child);
    }
    Ok(el.into_element())
}
