use pyo3::prelude::*;

mod app;
mod bridge;
mod signal;
mod tree;

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(app::run, m)?)?;
    m.add_function(wrap_pyfunction!(signal::in_engine, m)?)?;
    m.add_class::<signal::Trigger>()?;
    Ok(())
}
