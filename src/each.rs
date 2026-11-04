//! Keyed lists: `nsh.each(items, render, key=...)` as NSH's `each`.
//!
//! Python's `nsh._each.Each` is a child, not an element kind: like a
//! callable child, it is a region of its parent's children. NSH's `each`
//! keeps the rows of keys that stay (moving them when the order changes),
//! makes rows for new keys and disposes the others.
//!
//! - An item is a [`Obj`]: a Python object behind an `Rc`, so NSH can clone
//!   it without the GIL. Two are equal if they are the same object, or
//!   `==` in Python (asked under the GIL, an exception meaning "not
//!   equal"): an item that changes under a key renders its row again.
//! - A key is a [`Key`]: the Python key with its `hash()`, computed with
//!   the items in one GIL pass, compared with `==` like a dict key's.
//! - `render` runs untracked inside a region that reads the row's item
//!   only, so it runs once per row and again only if its item changes.

use std::{
    cell::{Cell, RefCell},
    hash::{Hash, Hasher},
    rc::Rc,
};

use nsh_core::{element::Reactive, prelude::*};
use pyo3::{exceptions::PyTypeError, prelude::*, sync::PyOnceLock};

use crate::{bridge, tree};

/// `nsh._each.Each`.
pub(crate) fn class(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
    static CLASS: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
    CLASS
        .get_or_try_init(py, || {
            Ok::<_, PyErr>(py.import("nsh._each")?.getattr("Each")?.unbind())
        })
        .map(|c| c.bind(py))
}

/// A Python object NSH can clone and compare: the same object, or `==`.
#[derive(Clone)]
struct Obj(Rc<Py<PyAny>>);

impl Obj {
    fn new(obj: &Bound<'_, PyAny>) -> Self {
        Obj(Rc::new(obj.clone().unbind()))
    }

    fn is(&self, other: &Obj) -> bool {
        self.0.as_ptr() == other.0.as_ptr()
    }
}

impl PartialEq for Obj {
    fn eq(&self, other: &Obj) -> bool {
        self.is(other)
            || Python::attach(|py| {
                self.0.bind(py).eq(other.0.bind(py)).unwrap_or_else(|err| {
                    bridge::report(py, err);
                    false
                })
            })
    }
}

/// A row's key.
#[derive(Clone)]
enum Key {
    /// A hashable key (`key(item)`, or the item itself), as a dict has it.
    Value { hash: isize, obj: Obj },
    /// An unhashable item with no `key`: known by identity.
    Identity(Obj),
    /// A key that failed: equal to nothing but itself.
    Unique(u64),
}

impl Hash for Key {
    fn hash<H: Hasher>(&self, state: &mut H) {
        match self {
            Key::Value { hash, .. } => hash.hash(state),
            Key::Identity(obj) => (obj.0.as_ptr() as usize).hash(state),
            Key::Unique(n) => n.hash(state),
        }
    }
}

impl PartialEq for Key {
    fn eq(&self, other: &Key) -> bool {
        match (self, other) {
            (Key::Value { hash: a, obj: x }, Key::Value { hash: b, obj: y }) => a == b && x == y,
            (Key::Identity(x), Key::Identity(y)) => x.is(y),
            (Key::Unique(a), Key::Unique(b)) => a == b,
            _ => false,
        }
    }
}

impl Eq for Key {}

/// An item and its key.
#[derive(Clone)]
struct Entry {
    item: Obj,
    key: Key,
}

impl PartialEq for Entry {
    /// The item alone: NSH compares entries of the same key, to tell
    /// whether the row's item changed.
    fn eq(&self, other: &Entry) -> bool {
        self.item == other.item
    }
}

/// How a list keys its items.
struct Keyer {
    key: Option<Py<PyAny>>,
    failed: Cell<u64>,
}

impl Keyer {
    /// The entries of `items`. A key that raises (or isn't hashable) is
    /// logged and replaced by a unique one.
    fn entries(&self, py: Python<'_>, items: &Bound<'_, PyAny>) -> PyResult<Vec<Entry>> {
        let mut out = Vec::new();
        for item in items.try_iter()? {
            let item = item?;
            let key = self.key(py, &item).unwrap_or_else(|err| {
                bridge::report(py, err);
                let n = self.failed.get();
                self.failed.set(n + 1);
                Key::Unique(n)
            });
            out.push(Entry {
                item: Obj::new(&item),
                key,
            });
        }
        Ok(out)
    }

    fn key(&self, py: Python<'_>, item: &Bound<'_, PyAny>) -> PyResult<Key> {
        match &self.key {
            Some(key) => {
                let key = key.bind(py).call1((item,))?;
                let hash = key.hash().map_err(|err| {
                    let wrapped = PyTypeError::new_err(format!(
                        "each: key must be hashable, got {}",
                        key.get_type().name().map_or("?".into(), |n| n.to_string())
                    ));
                    wrapped.set_cause(py, Some(err));
                    wrapped
                })?;
                Ok(Key::Value {
                    hash,
                    obj: Obj::new(&key),
                })
            }
            None => Ok(match item.hash() {
                Ok(hash) => Key::Value {
                    hash,
                    obj: Obj::new(item),
                },
                Err(_) => Key::Identity(Obj::new(item)),
            }),
        }
    }
}

/// The region an `nsh._each.Each` stands for.
pub(crate) fn build(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<AnyElement> {
    let items = obj.getattr("items")?;
    let render = obj.getattr("render")?.unbind();
    let key = obj.getattr("key")?;
    let keyer = Rc::new(Keyer {
        key: (!key.is_none()).then(|| key.unbind()),
        failed: Cell::new(0),
    });

    let items: Reactive<Vec<Entry>> = if items.is_callable() {
        let items = items.unbind();
        let keyer = keyer.clone();
        // A failed run keeps the rows shown: dropping them would lose
        // their state for an error that may pass.
        let last = RefCell::new(Vec::new());
        Reactive::Bound(Rc::new(move || {
            let entries = bridge::call(|py| keyer.entries(py, &items.bind(py).call0()?));
            if let Some(entries) = entries {
                last.replace(entries);
            }
            last.borrow().clone()
        }))
    } else {
        Reactive::Static(keyer.entries(py, &items)?)
    };
    let render = Rc::new(render);
    Ok(each(
        items,
        |entry: &Entry| entry.key.clone(),
        move |item: ReadSignal<Entry>, _index| {
            let render = render.clone();
            dynamic(move || {
                // Only the item is tracked: what `render` reads it reads
                // once, as a component does.
                let entry = item.get();
                untracked(|| {
                    bridge::call(|py| {
                        tree::children(py, &render.bind(py).call1((&*entry.item.0,))?)
                    })
                    .unwrap_or_default()
                })
            })
        },
    ))
}
