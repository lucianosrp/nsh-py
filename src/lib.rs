use pyo3::prelude::*;

mod app;
mod bridge;
mod tree;

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(app::run, m)?)?;
    Ok(())
}
