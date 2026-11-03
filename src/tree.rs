//! Python element trees as NSH elements: the children of anything.
//!
//! Python builds plain `nsh.Element` objects (`kind`, `props`,
//! `children`); this module walks them on the engine thread and hands each
//! element to its kind's builder (`crate::elements`). A callable child is a
//! region made again when the signals it read change (`dynamic`).

use nsh_core::prelude::*;
use pyo3::{
    prelude::*,
    sync::PyOnceLock,
    types::{PyDict, PyList, PyString, PyTuple},
};

use crate::{bridge, elements};

/// `nsh._element.Element`.
fn element_class(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
    static CLASS: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
    CLASS
        .get_or_try_init(py, || {
            Ok::<_, PyErr>(py.import("nsh._element")?.getattr("Element")?.unbind())
        })
        .map(|c| c.bind(py))
}

/// The elements `obj` stands for, as a child: an `Element`, a string (a
/// text), `None` (nothing), a list or tuple of children, or a callable
/// returning children (a region made again when what it reads changes).
pub(crate) fn children(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Vec<AnyElement>> {
    if obj.is_none() {
        return Ok(Vec::new());
    }
    if obj.is_instance(element_class(py)?)? {
        return Ok(vec![element(py, obj)?]);
    }
    if obj.is_instance_of::<PyString>() {
        return Ok(vec![text(obj.extract::<String>()?).into_element()]);
    }
    if obj.is_instance_of::<PyList>() || obj.is_instance_of::<PyTuple>() {
        let mut out = Vec::new();
        for child in obj.try_iter()? {
            out.extend(children(py, &child?)?);
        }
        return Ok(out);
    }
    if obj.is_callable() {
        let f = obj.clone().unbind();
        return Ok(vec![dynamic(move || {
            bridge::call(|py| children(py, &f.bind(py).call0()?)).unwrap_or_default()
        })]);
    }
    // Anything else shows as its `str()` (numbers, say).
    Ok(vec![text(obj.str()?.to_string()).into_element()])
}

/// One `nsh.Element`, built by its kind's builder.
fn element(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<AnyElement> {
    let kind: String = obj.getattr("kind")?.extract()?;
    let props = obj.getattr("props")?.cast_into::<PyDict>()?;
    let kids = obj.getattr("children")?;
    let build = elements::builder(&kind).ok_or_else(|| {
        pyo3::exceptions::PyValueError::new_err(format!(
            "unknown element kind {kind:?} (known: {})",
            elements::kinds().join(", ")
        ))
    })?;
    build(py, &props, &kids)
}
