"""Native UIs in plain Python, powered by Native Shell (NSH)."""

from nsh._component import Component
from nsh._core import __version__
from nsh._dialog import alert_dialog
from nsh._each import Each, each
from nsh._element import Element
from nsh._engine import Effect, Timer, call_soon, effect, set_interval, set_timeout
from nsh._runtime import run
from nsh._signals import Computed, Signal, computed, signal
from nsh._window import Window, current_window, quit
from nsh.components import alert, badge, button, card, separator, skeleton, table
from nsh.primitives import (
    checkbox,
    image,
    input,
    progress,
    scroll,
    select,
    slider,
    switch,
    tab,
    tabs,
    text,
    video,
    view,
)
from nsh.primitives.video import Video, VideoInfo, VideoProgress

__all__ = [
    "Component",
    "Computed",
    "Each",
    "Effect",
    "Element",
    "Signal",
    "Timer",
    "Video",
    "VideoInfo",
    "VideoProgress",
    "Window",
    "__version__",
    "alert",
    "alert_dialog",
    "badge",
    "button",
    "call_soon",
    "card",
    "checkbox",
    "computed",
    "current_window",
    "each",
    "effect",
    "image",
    "input",
    "progress",
    "quit",
    "run",
    "scroll",
    "select",
    "separator",
    "set_interval",
    "set_timeout",
    "signal",
    "skeleton",
    "slider",
    "switch",
    "tab",
    "table",
    "tabs",
    "text",
    "video",
    "view",
]
