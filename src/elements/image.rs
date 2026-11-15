//! `image`: a picture (`nsh.image`).
//!
//! Props: `src` (a path, `http(s)://` / `data:` / `file:` / `asset:` URI,
//! bytes, or a callable returning one), `alt` (screen-reader label),
//! `fit` (`contain`, `cover`, `fill`, `none`, `scale-down`), plus the
//! common props (`class_`, `test_id`). Relative paths are made absolute
//! ([`props::uri`]).

use std::rc::Rc;

use nsh_core::{
    element::{ImageSrc, Reactive, image},
    prelude::*,
};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyByteArray, PyBytes, PyDict},
};

use crate::{bridge, props};

pub(super) fn build(
    _py: Python<'_>,
    props: &Bound<'_, PyDict>,
    _children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let src = match props::get(props, "src")? {
        Some(src) => src_reactive(&src)?,
        None => return Err(PyValueError::new_err("image needs src")),
    };
    let mut el = image(src);
    if let Some(alt) = props::get(props, "alt")? {
        el = el.label(props::string(&alt)?);
    }
    if let Some(fit) = props::get(props, "fit")? {
        el = el.object_fit(props::fit(&fit, ResizeMode::Cover)?);
    }
    Ok(props::common(el, props)?.into_element())
}

fn src_reactive(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<ImageSrc>> {
    if obj.is_callable() {
        let f = obj.clone().unbind();
        Ok(Reactive::Bound(Rc::new(move || {
            bridge::call(|py| to_src(&f.bind(py).call0()?)).unwrap_or_else(|| ImageSrc::from(""))
        })))
    } else {
        Ok(Reactive::Static(to_src(obj)?))
    }
}

fn to_src(obj: &Bound<'_, PyAny>) -> PyResult<ImageSrc> {
    Ok(ImageSrc::from(src_uri(obj)?))
}

/// What `obj` names, as a URI NSH can load ([`props::uri`]); bytes
/// become a `data:` URI.
fn src_uri(obj: &Bound<'_, PyAny>) -> PyResult<String> {
    if obj.is_instance_of::<PyBytes>() || obj.is_instance_of::<PyByteArray>() {
        let bytes: Vec<u8> = obj.extract()?;
        return Ok(data_uri(&bytes));
    }
    props::uri(obj)
}

fn data_uri(bytes: &[u8]) -> String {
    let mime = image_mime(bytes).unwrap_or("application/octet-stream");
    format!("data:{mime};base64,{}", base64(bytes))
}

fn image_mime(bytes: &[u8]) -> Option<&'static str> {
    nsh_core::platform::clipboard::image_mime(bytes)
}

fn base64(data: &[u8]) -> String {
    const T: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity(data.len().div_ceil(3) * 4);
    let mut i = 0;
    while i < data.len() {
        let b0 = data[i];
        let b1 = data.get(i + 1).copied();
        let b2 = data.get(i + 2).copied();
        out.push(T[(b0 >> 2) as usize] as char);
        out.push(T[(((b0 & 3) << 4) | b1.unwrap_or(0) >> 4) as usize] as char);
        match (b1, b2) {
            (Some(b1), Some(b2)) => {
                out.push(T[(((b1 & 0x0f) << 2) | (b2 >> 6)) as usize] as char);
                out.push(T[(b2 & 0x3f) as usize] as char);
            }
            (Some(b1), None) => {
                out.push(T[((b1 & 0x0f) << 2) as usize] as char);
                out.push('=');
            }
            (None, _) => {
                out.push('=');
                out.push('=');
            }
        }
        i += 3;
    }
    out
}
