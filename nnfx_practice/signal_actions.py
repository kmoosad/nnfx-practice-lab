"""Use a fresh strategy observation at the entry and exit calculation boundaries."""

from math import isfinite
from typing import Literal


Direction = Literal["long", "short"]
Signal = Literal["long", "short", "no_event", "unavailable"]


def exit_reasons(position: Direction, *, c1: Signal, exit_signal: Signal) -> tuple[str, ...]:
    """Either independently calculated opposite event can close the position."""
    opposite = {"long": "short", "short": "long"}[position]
    return tuple(name for name, event in (("c1", c1), ("exit", exit_signal)) if event == opposite)


def entry_signal(c1: Signal, atr: float | None) -> tuple[Direction, str] | None:
    """Return the fresh direction and round-trippable sizing ATR when both are usable."""
    if c1 in ("long", "short") and type(atr) in (int, float) and isfinite(atr) and atr > 0:
        return c1, str(atr)
    return None
