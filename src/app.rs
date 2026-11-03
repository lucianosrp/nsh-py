//! `nsh.run()`: opens a window on the platform's main loop.
//!
//! The calling thread (Python's main thread) runs the GTK/AppKit/Win32 loop
//! with the GIL released; the app's code runs on the "nsh-engine" thread
//! (see `docs/architecture.md`).

use std::sync::Mutex;

use nsh_core::prelude::*;
use pyo3::prelude::*;

#[cfg(target_os = "linux")]
use nsh_platform_linux as platform;
#[cfg(target_os = "macos")]
use nsh_platform_macos as platform;
#[cfg(target_os = "windows")]
use nsh_platform_windows as platform;

/// What the window shows: a component written in Rust (for the spike and
/// smoke tests) or a Python factory.
pub(crate) enum RootKind {
    /// `nsh.run(None)`: the built-in Rust hello component.
    Hello,
    /// A Python component: a callable returning elements, or elements.
    Python(Py<PyAny>),
}

/// The root of the app being run. One app per process: `run_app` owns the
/// main loop until the window closes.
pub(crate) static ROOT: Mutex<Option<RootKind>> = Mutex::new(None);

/// A component written in Rust, to check the platform works at all.
pub(crate) struct Hello;

impl Component for Hello {
    type Props = ();
    type Event = NoEvent;

    fn view(_: (), _cx: Scope<NoEvent>) -> impl IntoElement {
        view()
            .app_class(Some(SharedString::from(
                "flex-1 items-center justify-center gap-2 p-8 bg-background",
            )))
            .child(text("Hello from Rust").app_class(Some(SharedString::from(
                "text-3xl font-bold text-foreground",
            ))))
            .child(
                text(format!("nsh-py {}", env!("CARGO_PKG_VERSION")))
                    .app_class(Some(SharedString::from("text-muted-foreground"))),
            )
    }
}

/// The root component: the stored root, made on the engine thread.
pub(crate) struct AppRoot;

impl Component for AppRoot {
    type Props = ();
    type Event = NoEvent;

    fn view(_: (), cx: Scope<NoEvent>) -> impl IntoElement {
        let kind = ROOT.lock().unwrap_or_else(|e| e.into_inner()).take();
        match kind {
            Some(RootKind::Hello) | None => Hello::view((), cx).into_element(),
            Some(RootKind::Python(root)) => python_root(root),
        }
    }
}

/// The window's content made by Python root `root`; an error message if
/// it raised (the exception is logged).
fn python_root(root: Py<PyAny>) -> AnyElement {
    let made = crate::bridge::call(|py| {
        let root = root.bind(py);
        let tree = if root.is_callable() {
            root.call0()?
        } else {
            root.clone()
        };
        crate::tree::children(py, &tree)
    });
    let page = view().app_class(Some(SharedString::from("flex-1 bg-background")));
    match made {
        Some(children) => page.child(children).into_element(),
        None => {
            page.app_class(Some(SharedString::from("flex-1 bg-background p-8 gap-2")))
                .child(text("The app's root raised an exception").app_class(Some(
                    SharedString::from("text-xl font-bold text-destructive"),
                )))
                .child(
                    text("See the log for the traceback.")
                        .app_class(Some(SharedString::from("text-muted-foreground"))),
                )
                .into_element()
        }
    }
}

/// Runs the app until its window closes. Raises `KeyboardInterrupt` if
/// Ctrl-C stopped it.
#[pyfunction]
#[pyo3(signature = (root=None, *, title="nsh".to_owned(), size=(480, 640), app_id="dev.nsh_py.app".to_owned()))]
pub(crate) fn run(
    py: Python<'_>,
    root: Option<Py<PyAny>>,
    title: String,
    size: (i32, i32),
    app_id: String,
) -> PyResult<()> {
    let kind = match root {
        None => RootKind::Hello,
        Some(root) => RootKind::Python(root),
    };
    *ROOT.lock().unwrap_or_else(|e| e.into_inner()) = Some(kind);

    let interrupted = py.detach(move || {
        platform::set_ui_sets(vec![nsh_base::registry()]);
        let watcher = interrupt::install();
        let _ = platform::run_app(
            platform::AppSource::Rust(
                platform::Root::of::<AppRoot>()
                    .tokens(nsh_base::Theme::default().into_tokens())
                    .app_id(app_id.clone()),
            ),
            platform::AppOptions {
                title,
                size,
                app_id,
                ..Default::default()
            },
        );
        interrupt::finish(watcher)
    });
    match interrupted {
        Some(err) => Err(err),
        None => Ok(()),
    }
}

/// Ctrl-C: Python's SIGINT handler only sets a flag, which
/// `check_signals` turns into `KeyboardInterrupt` on the main thread. The
/// main thread is in the platform's loop, so a timer on that loop checks
/// it and quits the app.
#[cfg(target_os = "linux")]
mod interrupt {
    use std::{cell::RefCell, rc::Rc, time::Duration};

    use nsh_platform_linux::gtk4::{gio, glib, prelude::*};
    use pyo3::prelude::*;

    pub(super) struct Watcher {
        source: Option<glib::SourceId>,
        error: Rc<RefCell<Option<PyErr>>>,
    }

    pub(super) fn install() -> Watcher {
        let error: Rc<RefCell<Option<PyErr>>> = Rc::default();
        let seen = error.clone();
        let source = glib::timeout_add_local(Duration::from_millis(100), move || {
            let result = Python::attach(|py| py.check_signals());
            match result {
                Ok(()) => glib::ControlFlow::Continue,
                Err(err) => {
                    *seen.borrow_mut() = Some(err);
                    if let Some(app) = gio::Application::default() {
                        app.quit();
                    }
                    glib::ControlFlow::Break
                }
            }
        });
        Watcher {
            source: Some(source),
            error,
        }
    }

    pub(super) fn finish(mut watcher: Watcher) -> Option<PyErr> {
        let error = watcher.error.borrow_mut().take();
        if error.is_none()
            && let Some(source) = watcher.source.take()
        {
            source.remove();
        }
        error
    }
}

/// Ctrl-C on macOS and Windows: not wired yet (roadmap step 2 is Linux).
#[cfg(not(target_os = "linux"))]
mod interrupt {
    use pyo3::prelude::*;

    pub(super) struct Watcher;

    pub(super) fn install() -> Watcher {
        Watcher
    }

    pub(super) fn finish(_: Watcher) -> Option<PyErr> {
        None
    }
}
