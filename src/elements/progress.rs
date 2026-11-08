//! `progress`: nsh-base's `Progress`, a linear progress bar
//! (`nsh.progress`).
//!
//! Props: `value` (a number or a callable) out of `max` (a number,
//! default 100; nsh-base takes a percentage, so the value is scaled and
//! held to 0..=100), `indeterminate` (a bool or a callable: no value, the
//! indicator's width is its classes'), `track_class` and `indicator_class`
//! (the parts' classes), plus `class_` (on a view around it:
//! `props::with_class`) and `test_id` (`props::test_probe`). The children
//! (a label) come under the track.

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

use crate::{props, tree};

pub(super) fn build(
    py: Python<'_>,
    props: &Bound<'_, PyDict>,
    children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let mut el = nsh_base::progress();
    let max = match props::get(props, "max")? {
        Some(max) => max.extract::<f32>()?,
        None => 100.0,
    };
    if !(max.is_finite() && max > 0.0) {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "progress max must be a positive number, not {max}"
        )));
    }
    if let Some(value) = props::get(props, "value")? {
        el = el.value(props::number(&value)?.map(move |v| v / max * 100.0));
    }
    if let Some(indeterminate) = props::get(props, "indeterminate")? {
        el = el.indeterminate(props::boolean(&indeterminate)?);
    }
    el = el
        .track_class(props::optional_string(props, "track_class")?)
        .indicator_class(props::optional_string(props, "indicator_class")?);
    for child in tree::children(py, children)? {
        el = el.child(child);
    }
    if let Some(probe) = props::test_probe(props)? {
        el = el.child(probe);
    }
    props::with_class(el, props)
}
