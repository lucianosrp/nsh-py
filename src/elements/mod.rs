//! The element kinds Python can build: one file per kind.
//!
//! To add a kind: write `<kind>.rs` with a `build` function, add it to
//! [`KINDS`], and add its Python function in `python/nsh/primitives/`
//! (`tests/test_kinds.py` checks the two lists match). See
//! CONTRIBUTING.md.

use nsh_core::prelude::*;
use pyo3::{prelude::*, types::PyDict};

mod checkbox;
mod input;
mod scroll;
mod switch;
mod text;
mod view;

/// Builds one element of a kind from its props and children.
pub(crate) type Build =
    fn(Python<'_>, &Bound<'_, PyDict>, &Bound<'_, PyAny>) -> PyResult<AnyElement>;

/// Every kind, by the name Python's `Element.kind` uses.
const KINDS: &[(&str, Build)] = &[
    ("checkbox", checkbox::build),
    ("input", input::build),
    ("scroll", scroll::build),
    ("switch", switch::build),
    ("text", text::build),
    ("view", view::build),
];

/// The builder of `kind`.
pub(crate) fn builder(kind: &str) -> Option<Build> {
    KINDS.iter().find(|(k, _)| *k == kind).map(|(_, b)| *b)
}

/// The kinds' names.
pub(crate) fn kinds() -> Vec<&'static str> {
    KINDS.iter().map(|(k, _)| *k).collect()
}

/// The element kinds this build of nsh knows.
#[pyfunction]
pub(crate) fn element_kinds() -> Vec<&'static str> {
    kinds()
}
