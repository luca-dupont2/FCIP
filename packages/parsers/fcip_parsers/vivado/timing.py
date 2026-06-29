from __future__ import annotations

import re
import json
from pathlib import Path

import structlog

from fcip_parsers.base import (
    ReportParser,
    TimingResult,
    UtilizationResult,
    RuntimeResult,
    ParseResult,
    ClockDomainTiming,
    CriticalPath,
)

logger = structlog.get_logger(__name__)


class VivadoTimingParser:
    def parse(self, content: str, source_file: str = "") -> ParseResult[TimingResult]:
        errors: list[str] = []
        warnings: list[str] = []

        if not content.strip():
            return ParseResult(success=False, errors=["empty timing report"])

        try:
            clock_domains = self._parse_clock_domains(content)
            if not clock_domains:
                warnings.append("no clock domain timing data found")

            wns = min((d.wns for d in clock_domains), default=0.0)
            tns = sum(d.tns for d in clock_domains)
            total_failing = sum(d.failing_paths for d in clock_domains)

            critical_path = self._parse_critical_path(content)

            return ParseResult(
                success=True,
                data=TimingResult(
                    wns=wns,
                    tns=tns,
                    failing_paths=total_failing,
                    critical_path=critical_path,
                    clock_domains=clock_domains,
                ),
                warnings=warnings,
            )
        except Exception as e:
            logger.error("vivado_timing_parse_failed", source=source_file, error=str(e))
            return ParseResult(success=False, errors=[f"parse error: {e}"])

    def _parse_clock_domains(self, content: str) -> list[ClockDomainTiming]:
        domains: list[ClockDomainTiming] = []

        pattern = re.compile(
            r"(-+\n\s*Clock\s+.*?\n-+\n(?:.*\n)*?)(?=-+\n\s*Clock\s+|$)",
            re.MULTILINE,
        )

        table_pattern = re.compile(
            r"^\s*(\S+)\s+\|\s*([-\d.]+)\s+\|\s*([-\d.]+)\s+\|\s*(\d+)",
            re.MULTILINE,
        )

        in_timing_section = False
        current_block: list[str] = []

        lines = content.split("\n")
        for line in lines:
            if re.search(r"Timing Summary", line, re.IGNORECASE):
                in_timing_section = True
                current_block = []
                continue
            if in_timing_section:
                if re.match(r"-{5,}", line):
                    if current_block:
                        text = "\n".join(current_block)
                        for m in table_pattern.finditer(text):
                            clock = m.group(1).strip()
                            wns_val = float(m.group(2))
                            tns_val = float(m.group(3))
                            failing = int(m.group(4))
                            domains.append(ClockDomainTiming(
                                clock=clock, wns=wns_val, tns=tns_val, failing_paths=failing
                            ))
                        current_block = []
                    continue
                current_block.append(line)

        if not domains:
            fallback = re.compile(
                r"^\s*([a-zA-Z_][\w.$\[\]]*)\s*\|?\s*([-\d.]+)\s*\|?\s*([-\d.]+)\s*\|?\s*(\d+)",
                re.MULTILINE,
            )
            for m in fallback.finditer(content):
                clock = m.group(1).strip()
                try:
                    wns_val = float(m.group(2))
                    tns_val = float(m.group(3))
                    failing = int(m.group(4))
                    domains.append(ClockDomainTiming(
                        clock=clock, wns=wns_val, tns=tns_val, failing_paths=failing
                    ))
                except ValueError:
                    continue

        return domains

    def _parse_critical_path(self, content: str) -> CriticalPath | None:
        max_delay_pattern = re.compile(
            r"Max Delay Path[:\s]+(.*?)(?=\n\n|\nMax Delay Path)",
            re.DOTALL | re.IGNORECASE,
        )
        slack_pattern = re.compile(r"Slack\s*[:=]\s*([-\d.]+)", re.IGNORECASE)
        source_pattern = re.compile(r"Source\s*:\s*(\S+)", re.IGNORECASE)
        dest_pattern = re.compile(r"Destination\s*:\s*(\S+)", re.IGNORECASE)
        data_path_pattern = re.compile(r"Data Path Delay\s*:\s*([-\d.]+)", re.IGNORECASE)
        logic_levels_pattern = re.compile(r"Logic Levels\s*:\s*(\d+)", re.IGNORECASE)

        slack_match = slack_pattern.search(content)
        if not slack_match:
            return None

        try:
            slack = float(slack_match.group(1))
            source = source_pattern.search(content)
            dest = dest_pattern.search(content)
            data_path = data_path_pattern.search(content)
            logic_levels = logic_levels_pattern.search(content)

            return CriticalPath(
                source=source.group(1) if source else "unknown",
                destination=dest.group(1) if dest else "unknown",
                slack=slack,
                data_path_delay=float(data_path.group(1)) if data_path else None,
                logic_levels=int(logic_levels.group(1)) if logic_levels else None,
            )
        except (ValueError, IndexError):
            return None


class VivadoUtilizationParser:
    def parse(self, content: str, source_file: str = "") -> ParseResult[UtilizationResult]:
        errors: list[str] = []
        warnings: list[str] = []

        if not content.strip():
            return ParseResult(success=False, errors=["empty utilization report"])

        try:
            lut = self._extract_resource(content, "CLB LUTs|Slice LUTs")
            lut_avail = self._extract_available(content, "CLB LUTs|Slice LUTs")
            ff = self._extract_resource(content, "CLB Registers|Slice Registers")
            ff_avail = self._extract_available(content, "CLB Registers|Slice Registers")
            bram = self._extract_resource(content, "Block RAM|BRAM")
            bram_avail = self._extract_available(content, "Block RAM|BRAM")
            dsp = self._extract_resource(content, "DSPs|DSP48")
            dsp_avail = self._extract_available(content, "DSPs|DSP48")
            io_used = self._extract_resource(content, "IO")
            io_avail = self._extract_available(content, "IO")
            clock_util = self._extract_clock_util(content)

            if lut is None and ff is None and bram is None:
                return ParseResult(success=False, errors=["no utilization data found"])

            return ParseResult(
                success=True,
                data=UtilizationResult(
                    lut=lut or 0,
                    lut_available=lut_avail or 0,
                    ff=ff or 0,
                    ff_available=ff_avail or 0,
                    bram=bram or 0,
                    bram_available=bram_avail or 0,
                    dsp=dsp or 0,
                    dsp_available=dsp_avail or 0,
                    io_used=io_used or 0,
                    io_available=io_avail or 0,
                    clock_utilization=clock_util,
                ),
                warnings=warnings,
            )
        except Exception as e:
            logger.error("vivado_utilization_parse_failed", source=source_file, error=str(e))
            return ParseResult(success=False, errors=[f"parse error: {e}"])

    def _extract_resource(self, content: str, label_pattern: str) -> int | None:
        for label in label_pattern.split("|"):
            pattern = re.compile(
                rf"^\s*{re.escape(label)}[^|]*\|\s*(\d+)",
                re.MULTILINE | re.IGNORECASE,
            )
            match = pattern.search(content)
            if match:
                return int(match.group(1))
        return None

    def _extract_available(self, content: str, label_pattern: str) -> int | None:
        for label in label_pattern.split("|"):
            patterns = [
                re.compile(
                    rf"^\s*{re.escape(label)}[^|]*\|[^|]*\|\s*(\d+)",
                    re.MULTILINE | re.IGNORECASE,
                ),
                re.compile(
                    rf"{re.escape(label)}[^|]*\|\s*\d+\s*\|\s*(\d+)",
                    re.IGNORECASE,
                ),
            ]
            for pat in patterns:
                match = pat.search(content)
                if match:
                    return int(match.group(1))
        return None

    def _extract_clock_util(self, content: str) -> float | None:
        pattern = re.compile(r"Clocking\s*\|?\s*[\d.]+\s*%?\s*\|?\s*([-\d.]+)\s*%?", re.IGNORECASE)
        match = pattern.search(content)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None


class VivadoRuntimeParser:
    def parse(self, content: str, source_file: str = "") -> ParseResult[RuntimeResult]:
        errors: list[str] = []
        warnings: list[str] = []

        if not content.strip():
            return ParseResult(success=False, errors=["empty log file"])

        try:
            synthesis_start = self._find_timestamp(content, r"Starting RTL Synthesis")
            synthesis_end = self._find_timestamp(content, r"Finished RTL Synthesis|RTL Synthesis Complete|synth_design completed")
            impl_start = self._find_timestamp(content, r"Starting Implementation|Starting opt_design|Running opt_design")
            impl_end = self._find_timestamp(content, r"Implementation Complete|Finished Implementation|Place and Route complete")
            bitstream_start = self._find_timestamp(content, r"Starting Bitstream|Starting write_bitstream")
            bitstream_end = self._find_timestamp(content, r"Bitstream Generation Complete|write_bitstream completed|Finished Bitstream")

            synth_dur = None
            if synthesis_start and synthesis_end:
                synth_dur = (synthesis_end - synthesis_start).total_seconds()
            elif synthesis_start:
                warnings.append("synthesis start found but no end timestamp")

            impl_dur = None
            if impl_start and impl_end:
                impl_dur = (impl_end - impl_start).total_seconds()
            elif impl_start:
                warnings.append("implementation start found but no end timestamp")

            bit_dur = None
            if bitstream_start and bitstream_end:
                bit_dur = (bitstream_end - bitstream_start).total_seconds()

            total = None
            if synth_dur and impl_dur:
                total = synth_dur + impl_dur + (bit_dur or 0)

            total_pattern = re.compile(r"Total CPU time.*?(\d+:\d+:\d+)|Total runtime.*?(\d+)\s*s", re.IGNORECASE)
            m = total_pattern.search(content)
            if m and total is None:
                if m.group(2):
                    total = float(m.group(2))
                elif m.group(1):
                    parts = m.group(1).split(":")
                    total = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

            if synth_dur is None and impl_dur is None and total is None:
                return ParseResult(success=False, errors=["no runtime data found in log"])

            return ParseResult(
                success=True,
                data=RuntimeResult(
                    synthesis_duration=synth_dur,
                    implementation_duration=impl_dur,
                    bitstream_duration=bit_dur,
                    total_runtime=total,
                ),
                warnings=warnings,
            )
        except Exception as e:
            logger.error("vivado_runtime_parse_failed", source=source_file, error=str(e))
            return ParseResult(success=False, errors=[f"parse error: {e}"])

    def _find_timestamp(self, content: str, pattern: str) -> "datetime | None":
        from datetime import datetime
        ts_pattern = re.compile(
            rf"(\d{{4}}[/-]\d{{2}}[/-]\d{{2}}\s+\d{{2}}:\d{{2}}:\d{{2}}).*?{pattern}",
            re.IGNORECASE,
        )
        m = ts_pattern.search(content)
        if m and m.group(1):
            ts_str = m.group(1).replace("/", "-")
            try:
                return datetime.fromisoformat(ts_str)
            except ValueError:
                pass

        reverse_pattern = re.compile(
            rf"{pattern}.*?(\d{{4}}[/-]\d{{2}}[/-]\d{{2}}\s+\d{{2}}:\d{{2}}:\d{{2}})",
            re.IGNORECASE,
        )
        m = reverse_pattern.search(content)
        if m and m.group(1):
            ts_str = m.group(1).replace("/", "-")
            try:
                return datetime.fromisoformat(ts_str)
            except ValueError:
                pass

        return None


class VivadoReportParser(ReportParser):
    def __init__(self) -> None:
        self._timing = VivadoTimingParser()
        self._utilization = VivadoUtilizationParser()
        self._runtime = VivadoRuntimeParser()

    def parse_timing(self, content: str, source_file: str = "") -> ParseResult[TimingResult]:
        return self._timing.parse(content, source_file)

    def parse_utilization(self, content: str, source_file: str = "") -> ParseResult[UtilizationResult]:
        return self._utilization.parse(content, source_file)

    def parse_runtime(self, content: str, source_file: str = "") -> ParseResult[RuntimeResult]:
        return self._runtime.parse(content, source_file)


class VivadoProjectDetector:
    REPORT_PATTERNS = {
        "timing": ["*_timing_summary_routed.rpt", "*timing*.rpt"],
        "utilization": ["*_utilization_place.rpt", "*_utilization.rpt", "*utilization*.rpt"],
        "log": ["vivado.log", "*.log"],
    }

    def detect(self, project_path: str) -> dict[str, list[str]]:
        path = Path(project_path)
        results: dict[str, list[str]] = {"timing": [], "utilization": [], "log": []}

        for report_type, patterns in self.REPORT_PATTERNS.items():
            for pat in patterns:
                for f in path.rglob(pat):
                    if f.is_file():
                        results[report_type].append(str(f))

        return results
