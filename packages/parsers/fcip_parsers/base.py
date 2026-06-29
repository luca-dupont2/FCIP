from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, List, Optional, TypeVar


@dataclass
class ClockDomainTiming:
    clock: str
    wns: float
    tns: float
    failing_paths: int


@dataclass
class CriticalPath:
    source: str
    destination: str
    slack: float
    data_path_delay: float | None = None
    logic_levels: int | None = None


@dataclass
class TimingResult:
    wns: float
    tns: float
    failing_paths: int
    critical_path: CriticalPath | None = None
    clock_domains: list[ClockDomainTiming] = field(default_factory=list)


@dataclass
class UtilizationResult:
    lut: int
    lut_available: int
    ff: int
    ff_available: int
    bram: int
    bram_available: int
    dsp: int
    dsp_available: int
    io_used: int
    io_available: int
    clock_utilization: float | None = None


@dataclass
class RuntimeResult:
    synthesis_duration: float | None = None
    implementation_duration: float | None = None
    bitstream_duration: float | None = None
    total_runtime: float | None = None


@dataclass
class ParseResult(Generic[TypeVar("T")]):
    success: bool
    data: Optional[TypeVar("T")] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ReportParser(ABC):
    @abstractmethod
    def parse_timing(self, content: str, source_file: str = "") -> ParseResult[TimingResult]:
        ...

    @abstractmethod
    def parse_utilization(self, content: str, source_file: str = "") -> ParseResult[UtilizationResult]:
        ...

    @abstractmethod
    def parse_runtime(self, content: str, source_file: str = "") -> ParseResult[RuntimeResult]:
        ...
