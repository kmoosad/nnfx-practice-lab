"""The selected lab candle and aligned output types."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


OutputValue = int | float | bool | str | None


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: int | float
    high: int | float
    low: int | float
    close: int | float
    volume: int | float | None = None


@dataclass(frozen=True)
class IndicatorOutput:
    timestamps: tuple[datetime, ...]
    series: Mapping[str, tuple[OutputValue, ...]]

    def __post_init__(self) -> None:
        if not isinstance(self.timestamps, tuple):
            raise TypeError("timestamps must be a tuple")
        if not isinstance(self.series, Mapping):
            raise TypeError("series must be a mapping")
        for name, values in self.series.items():
            if not isinstance(name, str) or not isinstance(values, tuple):
                raise TypeError("series entries must map names to tuples")
            if len(values) != len(self.timestamps):
                raise ValueError("output_alignment")
