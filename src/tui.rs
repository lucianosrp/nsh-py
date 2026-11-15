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
    let session = Session::enter(mouse)?;
    let mut options = AppOptions::default();
    options.ui_sets = vec![nsh_base::registry()];
    options.capabilities = capabilities(&session.colors);
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
    /// What the terminal said about its colours.
    colors: Colors,
}

impl Session {
    fn enter(mouse: bool) -> io::Result<Self> {
        terminal::enable_raw_mode()?;
        // In raw mode, so the answers aren't echoed, and before crossterm's
        // reader starts, so they are ours to read.
        let colors = query_colors();
        let session = Self { mouse, colors };
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

/// The terminal's default colours, as it answers OSC 10 and OSC 11.
#[derive(Debug, Default, Clone, Copy, PartialEq)]
struct Colors {
    foreground: Option<[u8; 3]>,
    background: Option<[u8; 3]>,
}

/// Asks for the default foreground (OSC 10) and background (OSC 11), then
/// the primary device attributes (DA1): every terminal answers DA1, so its
/// answer ends the wait. A terminal that answers none of them costs
/// `QUERY_TIMEOUT` at startup.
#[cfg(unix)]
fn query_colors() -> Colors {
    const QUERY: &[u8] = b"\x1b]10;?\x1b\\\x1b]11;?\x1b\\\x1b[c";
    const QUERY_TIMEOUT: Duration = Duration::from_secs(1);
    // SAFETY: isatty only inspects the descriptors.
    let tty =
        unsafe { libc::isatty(libc::STDIN_FILENO) == 1 && libc::isatty(libc::STDOUT_FILENO) == 1 };
    if !tty {
        return Colors::default(); // nothing would answer
    }
    let mut out = io::stdout();
    if out.write_all(QUERY).and_then(|()| out.flush()).is_err() {
        return Colors::default();
    }
    let deadline = std::time::Instant::now() + QUERY_TIMEOUT;
    let mut replies = Vec::new();
    let mut chunk = [0u8; 512];
    loop {
        let (colors, complete) = parse_replies(&replies);
        let left = deadline.saturating_duration_since(std::time::Instant::now());
        if complete || left.is_zero() {
            return colors;
        }
        let mut fd = libc::pollfd {
            fd: libc::STDIN_FILENO,
            events: libc::POLLIN,
            revents: 0,
        };
        let wait = left.as_millis().clamp(1, i32::MAX as u128) as libc::c_int;
        // SAFETY: `fd` is initialised and lives through this bounded wait.
        let ready = unsafe { libc::poll(&mut fd, 1, wait) };
        if ready < 0 {
            if io::Error::last_os_error().kind() == io::ErrorKind::Interrupted {
                continue;
            }
            return colors;
        }
        if ready == 0 {
            continue;
        }
        if fd.revents & (libc::POLLHUP | libc::POLLERR | libc::POLLNVAL) != 0 {
            return colors;
        }
        // SAFETY: `chunk` is writable for its length; poll said stdin has data.
        let read =
            unsafe { libc::read(libc::STDIN_FILENO, chunk.as_mut_ptr().cast(), chunk.len()) };
        if read <= 0 {
            return colors;
        }
        replies.extend_from_slice(&chunk[..read as usize]);
    }
}

/// Windows: not asked yet, so the surfaces are drawn without fills.
#[cfg(not(unix))]
fn query_colors() -> Colors {
    Colors::default()
}

/// The colours in the terminal's answers (`ESC ] 1x ; rgb:RRRR/GGGG/BBBB`,
/// ended by BEL or ST), and whether DA1 (`CSI ? ... c`) closed them.
fn parse_replies(bytes: &[u8]) -> (Colors, bool) {
    let mut colors = Colors::default();
    let mut complete = false;
    let mut i = 0;
    while i + 1 < bytes.len() {
        if bytes[i] != 0x1b {
            i += 1;
            continue;
        }
        let body = &bytes[i + 2..];
        match bytes[i + 1] {
            b']' => {
                let end = body
                    .iter()
                    .position(|&b| b == 0x07 || b == 0x1b)
                    .unwrap_or(body.len());
                let text = String::from_utf8_lossy(&body[..end]);
                if let Some((code, value)) = text.split_once(';') {
                    match code {
                        "10" => colors.foreground = parse_color(value).or(colors.foreground),
                        "11" => colors.background = parse_color(value).or(colors.background),
                        _ => {}
                    }
                }
                i += 2 + end;
            }
            b'[' => {
                let Some(end) = body.iter().position(|b| (0x40..=0x7e).contains(b)) else {
                    break; // the rest hasn't arrived yet
                };
                complete |= body.first() == Some(&b'?') && body[end] == b'c';
                i += 3 + end;
            }
            _ => i += 1,
        }
    }
    (colors, complete)
}

/// An X11 colour as terminals answer it: `rgb:` (or `rgba:`) with one to
/// four hex digits per channel, scaled to eight bits.
fn parse_color(value: &str) -> Option<[u8; 3]> {
    let channels = value
        .strip_prefix("rgb:")
        .or_else(|| value.strip_prefix("rgba:"))?;
    let mut out = [0; 3];
    let mut parts = channels.split('/');
    for slot in &mut out {
        let part = parts.next()?;
        if part.is_empty() || part.len() > 4 {
            return None;
        }
        let value = u32::from_str_radix(part, 16).ok()?;
        let max = (1u32 << (4 * part.len())) - 1;
        *slot = ((value * 255 + max / 2) / max) as u8;
    }
    Some(out)
}

/// Whether `[r, g, b]` is a light colour (relative luminance above 0.4).
fn is_light([r, g, b]: [u8; 3]) -> bool {
    let linear = |c: u8| {
        let c = f32::from(c) / 255.0;
        if c <= 0.04045 {
            c / 12.92
        } else {
            ((c + 0.055) / 1.055).powf(2.4)
        }
    };
    0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b) > 0.4
}

/// What the terminal answered and the environment says about colours. With
/// its background known, NSH draws filled surfaces (buttons, cards,
/// selections) as steps of it, and picks light or dark to match.
fn capabilities(colors: &Colors) -> TerminalCapabilities {
    let mut caps = TerminalCapabilities::default();
    caps.foreground_color = colors.foreground;
    caps.background_color = colors.background;
    if let Some(background) = colors.background {
        caps.background = if is_light(background) {
            nsh_core::platform::ColorScheme::Light
        } else {
            nsh_core::platform::ColorScheme::Dark
        };
    }
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
