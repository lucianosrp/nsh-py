//! `view`: a flexbox container (`nsh.view`).

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = props::common(view(), props)?;
    for child in tree::children(py, children)? {
        el = el.child(child);
    }
    Ok(el.into_element())
}
