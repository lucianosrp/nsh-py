//! `nsh.run(App, platform="tui")`: the app in the terminal.
//!
//! nsh-platform-tui draws an app on the terminal's character grid, but
//! leaves the terminal and the event loop to its host. This is that host:
//! crossterm sets the terminal up (raw mode, the alternate screen, mouse
//! reports), turns its events into the surface's input, and puts the
//! terminal back when the app ends. The calling thread (Python's main
//! thread) runs the loop with the GIL released; the app's code runs on the
//! engine thread, as with a window.
//!
//! The event conversion follows NSH's own host (`nsh-tui-host`, Apache-2.0).

use std::{
    io::{self, Write},
    time::Duration,
};

use nsh_platform_tui::{
    AppOptions, AppView, ColorDepth, Input, Modifiers, MouseButton, MouseInput, MouseKind,
    RunEvent, TerminalCapabilities, run_app,
};
use pyo3::{exceptions::PyOSError, prelude::*};
use ratatui_core::terminal::Terminal;
use ratatui_crossterm::{
    CrosstermBackend,
    crossterm::{cursor, event, execute, terminal},
};

/// Runs `root` in the terminal until it quits (Ctrl-C or Ctrl-Q).
#[pyfunction]
#[pyo3(signature = (root=None, *, mouse=true))]
pub(crate) fn run_tui(py: Python<'_>, root: Option<Py<PyAny>>, mouse: bool) -> PyResult<()> {
    crate::app::set_root(root);
    crate::queue::begin();
    let result = py.detach(move || {
        let result = run(mouse);
        crate::queue::end();
        result
    });
    result.map_err(|err| PyOSError::new_err(format!("the terminal app failed: {err}")))
}

fn run(mouse: bool) -> io::Result<()> {
    let _session = Session::enter(mouse)?;
    let mut options = AppOptions::default();
    options.ui_sets = vec![nsh_base::registry()];
    options.capabilities = capabilities();
    let mut view = AppView::new(options);
    let mut terminal = Terminal::new(CrosstermBackend::new(io::BufWriter::new(io::stdout())))?;
    // Draw once first, so the first layout has the terminal's size.
    terminal.draw(|frame| view.render(frame, frame.area()))?;
    view.load(crate::app::app_root())?;
    run_app(&mut terminal, &mut view, poll)
}

/// The terminal in raw mode on the alternate screen, for as long as it
/// lives (also when the app panics).
struct Session {
    mouse: bool,
}

impl Session {
    fn enter(mouse: bool) -> io::Result<Self> {
        terminal::enable_raw_mode()?;
        let session = Self { mouse };
        execute!(io::stdout(), terminal::EnterAlternateScreen, cursor::Hide)?;
        // Optional: a terminal without them ignores the sequences.
        let _ = execute!(
            io::stdout(),
            event::EnableBracketedPaste,
            event::EnableFocusChange
        );
        if mouse {
            execute!(io::stdout(), event::EnableMouseCapture)?;
        }
        Ok(session)
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        let mut out = io::stdout();
        if self.mouse {
            let _ = execute!(out, event::DisableMouseCapture);
        }
        let _ = execute!(
            out,
            event::DisableBracketedPaste,
            event::DisableFocusChange,
            cursor::Show,
            terminal::LeaveAlternateScreen
        );
        let _ = out.flush();
        let _ = terminal::disable_raw_mode();
    }
}

/// What the environment says about colors. The terminal's own background
/// isn't queried yet (OSC 11), so the surfaces are drawn without fills.
fn capabilities() -> TerminalCapabilities {
    let mut caps = TerminalCapabilities::default();
    let var = |name: &str| std::env::var(name).unwrap_or_default();
    caps.colors = if !var("NO_COLOR").is_empty() {
        ColorDepth::Monochrome
    } else if matches!(var("COLORTERM").as_str(), "truecolor" | "24bit") {
        ColorDepth::TrueColor
    } else if var("TERM").contains("256color") {
        ColorDepth::Ansi256
    } else {
        ColorDepth::Ansi16
    };
    caps
}

/// The next terminal event, waiting at most `timeout`.
fn poll(timeout: Duration) -> io::Result<RunEvent> {
    if event::poll(timeout)? {
        Ok(convert(event::read()?))
    } else {
        Ok(RunEvent::Idle)
    }
}

fn modifiers(keys: event::KeyModifiers) -> Modifiers {
    Modifiers {
        ctrl: keys.contains(event::KeyModifiers::CONTROL),
        alt: keys.contains(event::KeyModifiers::ALT),
        shift: keys.contains(event::KeyModifiers::SHIFT),
        cmd: keys.contains(event::KeyModifiers::SUPER),
    }
}

fn button(button: event::MouseButton) -> MouseButton {
    match button {
        event::MouseButton::Left => MouseButton::Left,
        event::MouseButton::Right => MouseButton::Right,
        event::MouseButton::Middle => MouseButton::Middle,
    }
}

/// A crossterm event as the surface's input; a resize is a redraw.
fn convert(event: event::Event) -> RunEvent {
    match event {
        event::Event::Resize(..) => RunEvent::Redraw,
        event::Event::FocusGained => RunEvent::Input(Input::Focus(true)),
        event::Event::FocusLost => RunEvent::Input(Input::Focus(false)),
        event::Event::Paste(text) => RunEvent::Input(Input::Paste(text)),
        event::Event::Mouse(mouse) => {
            let mut input = MouseInput::default();
            input.column = mouse.column;
            input.row = mouse.row;
            input.modifiers = modifiers(mouse.modifiers);
            input.kind = match mouse.kind {
                event::MouseEventKind::Down(b) => MouseKind::Down(button(b)),
                event::MouseEventKind::Up(b) => MouseKind::Up(button(b)),
                event::MouseEventKind::Moved | event::MouseEventKind::Drag(_) => MouseKind::Move,
                event::MouseEventKind::ScrollUp => MouseKind::Wheel { x: 0, y: -1 },
                event::MouseEventKind::ScrollDown => MouseKind::Wheel { x: 0, y: 1 },
                event::MouseEventKind::ScrollLeft => MouseKind::Wheel { x: -1, y: 0 },
                event::MouseEventKind::ScrollRight => MouseKind::Wheel { x: 1, y: 0 },
            };
            RunEvent::Input(Input::Mouse(input))
        }
        event::Event::Key(key) => {
            // Ctrl-C reaches the surface: it copies a selection, else quits.
            let name = match key.code {
                event::KeyCode::Char(c) => c.to_string(),
                event::KeyCode::Esc => "Escape".into(),
                event::KeyCode::BackTab => "Tab".into(),
                event::KeyCode::F(number) => format!("F{number}"),
                other => format!("{other:?}"),
            };
            let mut modifiers = modifiers(key.modifiers);
            if key.code == event::KeyCode::BackTab {
                modifiers.shift = true;
            }
            if key.kind == event::KeyEventKind::Repeat {
                RunEvent::Input(Input::KeyRepeat {
                    key: name,
                    modifiers,
                })
            } else {
                RunEvent::Input(Input::Key {
                    key: name,
                    modifiers,
                    release: key.kind == event::KeyEventKind::Release,
                })
            }
        }
    }
}
