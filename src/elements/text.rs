//! `text`: a text block (`nsh.text`). Prop `content`: a string, or a
//! callable for a bound one.

use nsh_core::{element::Reactive, prelude::*};
use pyo3::{prelude::*, types::PyDict};

use crate::props;

pub(super) fn build(
    _py: Python<'_>,
    props: &Bound<'_, PyDict>,
    _children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let content = match props::get(props, "content")? {
        Some(c) => props::string(&c)?,
        None => Reactive::Static(SharedString::default()),
    };
    Ok(props::common(text(content), props)?.into_element())
}
