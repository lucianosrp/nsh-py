"""Class components: `class Counter(nsh.Component)`.

    class Counter(nsh.Component):
        count: int = 0

        def bump(self):
            self.count += 1

        def view(self):
            return nsh.button(lambda: f"Count: {self.count}", on_press=self.bump)

Each annotated class attribute is the component's state: one signal per
instance, behind a descriptor. Reading `self.count` reads the signal (a
lambda that reads it follows it), and assigning `self.count = ...` sets
it, so `self.count += 1` redraws what shows the count.

It is sugar over function components, not a second model: `Counter()`
runs `setup()` and `view()` once and returns the elements, as calling a
function component does. Nothing re-renders; the lambdas update.
"""

from __future__ import annotations

import copy
import sys
from types import SimpleNamespace
from typing import Any, ClassVar, get_origin

from nsh import _signals
from nsh._signals import Signal

_REQUIRED: Any = object()
"""A field with an annotation and no default: the caller must pass it."""


class _Field:
    """One state field: `self.<name>` reads its signal, assigning sets it."""

    def __init__(self, name: str, default: Any) -> None:
        self.name = name
        self.default = default

    def __get__(self, obj: Any, owner: type | None = None) -> Any:
        if obj is None:
            return self
        return obj._nsh_state[self.name]()

    def __set__(self, obj: Any, value: Any) -> None:
        obj._nsh_state[self.name].set(value)

    def __repr__(self) -> str:
        return f"<state field {self.name}>"


def _annotations(cls: type) -> dict[str, Any]:
    """The class's own annotations, without evaluating them."""
    try:
        import annotationlib  # Python 3.14+: annotations are lazy

        return annotationlib.get_annotations(cls, format=annotationlib.Format.FORWARDREF)
    except ImportError:
        return dict(cls.__dict__.get("__annotations__", {}))


def _is_classvar(annotation: Any) -> bool:
    if isinstance(annotation, str):
        return annotation.startswith(("ClassVar", "typing.ClassVar"))
    return annotation is ClassVar or get_origin(annotation) is ClassVar


class _ComponentMeta(type):
    def __call__(cls, *args: Any, **props: Any) -> Any:
        """`Counter(...)` makes the component and returns its elements."""
        self = cls.__new__(cls)
        self._nsh_init(props)
        self.__init__(*args)
        self.setup()
        return self.view()


class Component(metaclass=_ComponentMeta):
    """A component written as a class. See the module docstring.

    - **State:** `count: int = 0` makes a field. Pass `Counter(count=5)` to
      start elsewhere, or pass a signal (`Counter(count=total)`) to share
      the parent's. A field with no default must be passed.
    - **`view()`** returns the elements, once. Read fields inside lambdas
      to keep them live: `lambda: f"{self.count}"`. A bare `self.count`
      outside a lambda is read once.
    - **`setup()`** runs before `view()`: timers, effects, derived values.
    - **`self.signals.<name>`** is a field's signal, for a widget that
      takes one (`nsh.checkbox("Done", checked=self.signals.done)`).
    - Changing a list or dict field in place doesn't redraw: assign a new
      one (`self.items = [*self.items, item]`).

    Unannotated class attributes and `ClassVar` ones are plain constants.
    """

    _nsh_fields: ClassVar[dict[str, _Field]] = {}
    _nsh_where: ClassVar[str] = ""
    _nsh_state: dict[str, Signal[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        fields = dict(cls._nsh_fields)  # inherited fields come first
        for name, annotation in _annotations(cls).items():
            if name.startswith("_") or _is_classvar(annotation):
                continue
            field = _Field(name, cls.__dict__.get(name, _REQUIRED))
            setattr(cls, name, field)
            fields[name] = field
        cls._nsh_fields = fields
        module = sys.modules.get(cls.__module__)
        cls._nsh_where = f"{getattr(module, '__file__', cls.__module__)}:{cls.__qualname__}"

    def _nsh_init(self, props: dict[str, Any]) -> None:
        unknown = props.keys() - self._nsh_fields.keys()
        if unknown:
            raise TypeError(
                f"{type(self).__name__}() got unexpected keyword argument(s): "
                f"{', '.join(sorted(unknown))}"
            )
        state: dict[str, Signal[Any]] = {}
        for name, field in self._nsh_fields.items():
            if name in props:
                value = props[name]
                if isinstance(value, Signal):  # shared with the caller
                    state[name] = value
                    continue
            elif field.default is _REQUIRED:
                raise TypeError(f"{type(self).__name__}() missing keyword argument: {name!r}")
            else:
                value = copy.copy(field.default)  # no list shared between instances
            state[name] = self._make_signal(value)
        object.__setattr__(self, "_nsh_state", state)

    def _make_signal(self, value: Any) -> Signal[Any]:
        # Hot reload keys a signal by where it was made. Here that would be
        # this file for every class, so name the class instead.
        hook = _signals._signal_hook
        if hook is not None:
            return hook(value, (self._nsh_where, self))
        return Signal(value)

    @property
    def signals(self) -> SimpleNamespace:
        """The fields' signals, by name: `self.signals.count`."""
        return SimpleNamespace(**self._nsh_state)

    def setup(self) -> None:
        """Runs once, before `view()`. Override it for timers and effects."""

    def view(self) -> Any:
        """The component's elements. Override it."""
        raise NotImplementedError(f"{type(self).__name__} must define view()")
