//! `tabs`: nsh-base owns the tab list, keyboard and accessibility.
//! Python owns the look (`class_`, `indicator_class`).

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = nsh_base::tabs();
    el = el.indicator_class(props::optional_string(props, "indicator_class")?);
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
