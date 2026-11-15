//! `video`: a video player (`nsh.video`).
//!
//! The events call Python with plain values, which `nsh.video` wraps in
//! named tuples. Times are seconds on the Python side, so
//! `progress_interval` is turned into NSH's milliseconds here.

use std::{
    sync::Mutex,
    thread::{self, ThreadId},
};

use nsh_core::prelude::*;
use pyo3::{exceptions::PyValueError, prelude::*, types::PyDict};

use crate::{bridge, props};

pub(super) fn build(
    _py: Python<'_>,
    props: &Bound<'_, PyDict>,
    _children: &Bound<'_, PyAny>,
) -> PyResult<AnyElement> {
    let src = match props::get(props, "src")? {
        Some(src) => src_reactive(&src)?,
        None => return Err(PyValueError::new_err("video needs src")),
    };
    let mut el = props::common(video(src), props)?;
    if let Some(paused) = props::get(props, "paused")? {
        el = el.paused(props::boolean(&paused)?);
    }
    if let Some(muted) = props::get(props, "muted")? {
        el = el.muted(props::boolean(&muted)?);
    }
    if let Some(repeat) = props::get(props, "repeat")? {
        el = el.repeat(props::boolean(&repeat)?);
    }
    if let Some(controls) = props::get(props, "controls")? {
        el = el.controls(props::boolean(&controls)?);
    }
    if let Some(volume) = props::get(props, "volume")? {
        el = el.volume(props::number(&volume)?);
    }
    if let Some(rate) = props::get(props, "rate")? {
        el = el.rate(props::number(&rate)?);
    }
    if let Some(seconds) = props::get(props, "progress_interval")? {
        el = el.progress_interval(props::number(&seconds)?.map(|s| s * 1000.0));
    }
    if let Some(fit) = props::get(props, "fit")? {
        el = el.object_fit(props::fit(&fit, ResizeMode::Contain)?);
    }
    if let Some(handler) = props::get(props, "on_load_start")? {
        let handler = handler.unbind();
        el = el.on_load_start(move || {
            bridge::call(|py| handler.call0(py).map(drop));
        });
    }
    if let Some(handler) = props::get(props, "on_load")? {
        let handler = handler.unbind();
        el = el.on_load(move |info: &VideoInfo| {
            let args = (info.duration, info.size.width.0, info.size.height.0);
            bridge::call(|py| handler.call1(py, args).map(drop));
        });
    }
    if let Some(handler) = props::get(props, "on_progress")? {
        let handler = handler.unbind();
        el = el.on_progress(move |p: &VideoProgress| {
            let args = (p.current_time, p.duration);
            bridge::call(|py| handler.call1(py, args).map(drop));
        });
    }
    if let Some(handler) = props::get(props, "on_buffer")? {
        el = el.on_buffer(props::with_bool(handler.unbind()));
    }
    if let Some(handler) = props::get(props, "on_end")? {
        let handler = handler.unbind();
        el = el.on_end(move || {
            bridge::call(|py| handler.call0(py).map(drop));
        });
    }
    if let Some(handler) = props::get(props, "on_error")? {
        let handler = handler.unbind();
        el = el.on_error(move |message: &str| {
            bridge::call(|py| handler.call1(py, (message,)).map(drop));
        });
    }
    if let Some(handle) = props::get(props, "ref")? {
        el = el.element_ref(&handle.cast::<VideoRef>()?.get().attach());
    }
    Ok(el.into_element())
}

fn src_reactive(obj: &Bound<'_, PyAny>) -> PyResult<Reactive<String>> {
    if obj.is_callable() {
        let f = obj.clone().unbind();
        Ok(Reactive::Bound(std::rc::Rc::new(move || {
            bridge::call(|py| props::uri(&f.bind(py).call0()?)).unwrap_or_default()
        })))
    } else {
        Ok(Reactive::Static(props::uri(obj)?))
    }
}

/// The NSH element ref of a built video, for `nsh.video`'s `seek`.
///
/// Not `unsendable`, as [`crate::signal::Trigger`] isn't: a `Video` element
/// may be made, dropped or seeked on any thread. The ref is a plain id that
/// only means something in the graph of the engine thread that made it.
#[pyclass(module = "nsh._core", frozen)]
pub(crate) struct VideoRef {
    made: Mutex<Option<(ThreadId, ElementRef)>>,
}

impl VideoRef {
    /// A fresh ref for the video being built, under the owner building it
    /// (a component, a region), which releases it when it goes. A video
    /// built again (its region re-ran) answers to the new ref.
    fn attach(&self) -> ElementRef {
        let handle = element_ref();
        *self.made.lock().unwrap_or_else(|e| e.into_inner()) =
            Some((thread::current().id(), handle));
        handle
    }
}

#[pymethods]
impl VideoRef {
    #[new]
    fn new() -> Self {
        VideoRef {
            made: Mutex::new(None),
        }
    }

    /// Jumps the video to `seconds`. On another thread than the engine's,
    /// the seek is posted there. Nothing happens while the video isn't
    /// shown.
    fn seek(&self, seconds: f64) {
        let Some((thread, handle)) = *self.made.lock().unwrap_or_else(|e| e.into_inner()) else {
            return;
        };
        let seek = move || {
            if thread::current().id() == thread {
                handle.seek(seconds);
            }
        };
        if bridge::in_engine() {
            seek();
        } else {
            let _ = crate::queue::post(Box::new(seek));
        }
    }
}
