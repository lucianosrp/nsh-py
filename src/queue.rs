//! The engine-thread queue: how code on any thread reaches the app.
//!
//! NSH's reactive graph belongs to the "nsh-engine" thread, so other
//! threads can't touch it. They post a job instead. A long-lived task on
//! the engine (the *pump*, started by the root component) drains the queue;
//! its `Waker` is `Send`, and waking it wakes the engine's loop, so a post
//! from a Python worker thread gets the engine to run the job soon, in the
//! order posted. The same path serves `nsh.call_soon`, signal writes from
//! other threads, and disposing effects and triggers from other threads.
//!
//! The queue is global (one app per process, see `app::ROOT`) and in one of
//! three states:
//!
//! - **Idle**: no app. [`post`] refuses and the caller decides (`call_soon`
//!   runs the function right away).
//! - **Starting**: an app was started (`nsh.run`, `nsh.testing.open`) but
//!   its pump isn't running yet. Jobs wait in the queue.
//! - **Running**: the pump is installed. Posting wakes it.
//!
//! The lock is only held to move jobs and the waker in and out. Jobs run
//! and drop outside it.

use std::{
    collections::VecDeque,
    future::Future,
    pin::Pin,
    sync::Mutex,
    task::{Context, Poll, Waker},
};

use pyo3::{prelude::*, types::PyTuple};

use crate::bridge;

/// Work for the engine thread.
pub(crate) type Job = Box<dyn FnOnce() + Send>;

enum State {
    Idle,
    Starting,
    /// The pump with this id is installed; wake it to run the jobs.
    Running(u64, Waker),
}

struct Queue {
    state: State,
    jobs: VecDeque<Job>,
    /// The id of the next pump.
    next_pump: u64,
}

static QUEUE: Mutex<Queue> = Mutex::new(Queue {
    state: State::Idle,
    jobs: VecDeque::new(),
    next_pump: 1,
});

fn queue() -> std::sync::MutexGuard<'static, Queue> {
    QUEUE.lock().unwrap_or_else(|e| e.into_inner())
}

/// An app is about to start: jobs posted from now wait for its pump.
pub(crate) fn begin() {
    let mut q = queue();
    if matches!(q.state, State::Idle) {
        q.state = State::Starting;
    }
}

/// The app ended (its engine thread is gone): back to Idle. Jobs still
/// waiting are dropped.
pub(crate) fn end() {
    let jobs = {
        let mut q = queue();
        q.state = State::Idle;
        std::mem::take(&mut q.jobs)
    };
    drop(jobs);
}

/// Whether an app is starting or running: posted jobs will be run.
pub(crate) fn active() -> bool {
    !matches!(queue().state, State::Idle)
}

/// Posts `job` to the engine thread. It runs after what is running now,
/// in the order posted, marked as inside the engine. Gives the job back if
/// no app is active.
pub(crate) fn post(job: Job) -> Result<(), Job> {
    let waker = {
        let mut q = queue();
        match &q.state {
            State::Idle => return Err(job),
            State::Starting => {
                q.jobs.push_back(job);
                return Ok(());
            }
            State::Running(_, waker) => {
                let waker = waker.clone();
                q.jobs.push_back(job);
                waker
            }
        }
    };
    waker.wake();
    Ok(())
}

/// Starts the pump. Called on the engine thread by the root component, so
/// the pump ends with the app (and its effects, made by jobs, belong to the
/// root).
pub(crate) fn install() {
    let id = {
        let mut q = queue();
        let id = q.next_pump;
        q.next_pump += 1;
        id
    };
    nsh_core::prelude::spawn(Pump { id });
}

/// Runs the queued jobs on the engine, and wakes itself while some are
/// left.
struct Pump {
    id: u64,
}

impl Future for Pump {
    type Output = ();

    fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<()> {
        // Only the jobs there are now: one that posts another doesn't starve
        // the engine's loop.
        let due = {
            let mut q = queue();
            if matches!(q.state, State::Starting | State::Running(..)) {
                q.state = State::Running(self.id, cx.waker().clone());
            }
            q.jobs.len()
        };
        for _ in 0..due {
            let job = queue().jobs.pop_front();
            match job {
                Some(job) => bridge::enter(job),
                None => break,
            }
        }
        if !queue().jobs.is_empty() {
            cx.waker().wake_by_ref();
        }
        Poll::Pending
    }
}

impl Drop for Pump {
    fn drop(&mut self) {
        // The engine's tasks end with their owner: later jobs wait for the
        // next pump, or for `end`.
        let mut q = queue();
        if matches!(q.state, State::Running(id, _) if id == self.id) {
            q.state = State::Starting;
        }
    }
}

/// Runs `fn(*args)` on the engine thread, soon: after what is running now
/// and what was posted before it, in order. Safe from any thread. Exceptions
/// are logged. With no app running it runs `fn(*args)` right away, on the
/// calling thread.
#[pyfunction]
#[pyo3(signature = (func, args=None))]
pub(crate) fn call_soon(py: Python<'_>, func: Py<PyAny>, args: Option<Py<PyTuple>>) {
    let args = args.unwrap_or_else(|| PyTuple::empty(py).unbind());
    if active() {
        let (job_func, job_args) = (func.clone_ref(py), args.clone_ref(py));
        let job: Job = Box::new(move || {
            bridge::call(|py| job_func.call1(py, job_args.bind(py)).map(drop));
        });
        if post(job).is_ok() {
            return;
        }
    }
    if let Err(err) = func.call1(py, args.bind(py)) {
        bridge::report(py, err);
    }
}

/// Whether an app is starting or running (jobs posted now will run).
#[pyfunction]
pub(crate) fn app_active() -> bool {
    active()
}

pub(crate) fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(call_soon, m)?)?;
    m.add_function(wrap_pyfunction!(app_active, m)?)
}
