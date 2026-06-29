from __future__ import annotations

import re
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


class QuartusTimingParser:
    def parse(self, content: str, source_file: str = "") -> ParseResult[TimingResult]:
        errors: list[str] = []
        warnings: list[str] = []

        if not content.strip():
            return ParseResult(success=False, errors=["empty timing report"])

        try:
            domains = self._parse_clock_domains(content)
            wns = min((d.wns for d in domains), default=0.0)
            tns = sum(d.tns for d in domains)
            total_failing = sum(d.failing_paths for d in domains)

            if not domains:
                slack = self._parse_slack_simple(content)
                if slack is not None:
                    wns = slack
                    tns = 0.0
                else:
                    warnings.append("no timing data found")

            critical_path = self._parse_critical_path(content)

            return ParseResult(
                success=True,
                data=TimingResult(
                    wns=wns,
                    tns=tns,
                    failing_paths=total_failing,
                    critical_path=critical_path,
                    clock_domains=domains,
                ),
                warnings=warnings,
            )
        except Exception as e:
            logger.error("quartus_timing_parse_failed", source=source_file, error=str(e))
            return ParseResult(success=False, errors=[f"parse error: {e}"])

    def _parse_clock_domains(self, content: str) -> list[ClockDomainTiming]:
        domains: list[ClockDomainTiming] = []

        pattern = re.compile(
            r"^\s*([-:\w.$\[\]]+)\s*\|?\s*([-\d.]+)\s*\|?\s*([-\d.]+)\s*\|?\s*(\d+)",
            re.MULTILINE,
        )

        in_section = False
        for line in content.split("\n"):
            if re.search(r"Clock.*Slack|Slack.*TNS|Slow .*$|Fast .*Model", line, re.IGNORECASE):
                in_section = True
                continue
            if in_section and re.match(r"^\s*$", line):
                in_section = False
                continue
            if not in_section:
                continue

            m = pattern.match(line)
            if m:
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

    def _parse_slack_simple(self, content: str) -> float | None:
        slack_pattern = re.compile(
            r"(?:Worst-case|Minimum)\s+(?:Slack|TNS)\s*[:=]\s*([-\d.]+)",
            re.IGNORECASE,
        )
        m = slack_pattern.search(content)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return None

    def _parse_critical_path(self, content: str) -> CriticalPath | None:
        slack_pattern = re.compile(r"Slack\s*[:=]\s*([-\d.]+)", re.IGNORECASE)
        source_pattern = re.compile(r"From\s*:\s*(\S+)", re.IGNORECASE)
        dest_pattern = re.compile(r"To\s*:\s*(\S+)", re.IGNORECASE)
        data_delay_pattern = re.compile(r"Data Delay\s*[:=]\s*([-\d.]+)", re.IGNORECASE)

        m = slack_pattern.search(content)
        if not m:
            return None

        try:
            slack = float(m.group(1))
            source = source_pattern.search(content)
            dest = dest_pattern.search(content)
            data_delay = data_delay_pattern.search(content)

            return CriticalPath(
                source=source.group(1) if source else "unknown",
                destination=dest.group(1) if dest else "unknown",
                slack=slack,
                data_path_delay=float(data_delay.group(1)) if data_delay else None,
            )
        except (ValueError, IndexError):
            return None


class QuartusUtilizationParser:
    def parse(self, content: str, source_file: str = "") -> ParseResult[UtilizationResult]:
        errors: list[str] = []
        warnings: list[str] = []

        if not content.strip():
            return ParseResult(success=False, errors=["empty utilization report"])

        try:
            alm = self._extract_value(content, r"Logic ALMs|ALMs|Adaptive Logic Modules")
            alm_avail = self._extract_available(content, r"Logic ALMs|ALMs|Adaptive Logic Modules")
            reg = self._extract_value(content, r"Registers|Dedicated Logic Registers")
            reg_avail = self._extract_available(content, r"Registers|Dedicated Logic Registers")
            m20k = self._extract_value(content, r"M20K|Block Memory|RAM")
            m20k_avail = self._extract_available(content, r"M20K|Block Memory|RAM")
            dsp = self._extract_value(content, r"DSP|DSP Blocks|DSP Elements")
            dsp_avail = self._extract_available(content, r"DSP|DSP Blocks|DSP Elements")
            io = self._extract_value(content, r"I/O|PIO|Pin")
            io_avail = self._extract_available(content, r"I/O|PIO|Pin")

            lut = alm if alm is not None else self._extract_value(content, r"LUT|LUTs")
            lut_avail = alm_avail if alm_avail is not None else self._extract_available(content, r"LUT|LUTs")
            ff = reg
            ff_avail = reg_avail
            bram = m20k
            bram_avail = m20k_avail

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
                    io_used=io or 0,
                    io_available=io_avail or 0,
                ),
                warnings=warnings,
            )
        except Exception as e:
            logger.error("quartus_utilization_parse_failed", source=source_file, error=str(e))
            return ParseResult(success=False, errors=[f"parse error: {e}"])

    def _extract_value(self, content: str, label_pattern: str) -> int | None:
        for label in label_pattern.split("|"):
            patterns = [
                re.compile(
                    rf"^\s*{re.escape(label)}\s*[^/\n]*?(\d+)",
                    re.MULTILINE | re.IGNORECASE,
                ),
                re.compile(
                    rf"{re.escape(label)}\s*[:/]\s*(\d+)",
                    re.IGNORECASE,
                ),
                re.compile(
                    rf"{re.escape(label)}\s+(?:.*?)\s+(\d+)\s*/\s*(\d+)",
                    re.IGNORECASE,
                ),
            ]
            for pat in patterns:
                m = pat.search(content)
                if m:
                    return int(m.group(1))
        return None

    def _extract_available(self, content: str, label_pattern: str) -> int | None:
        for label in label_pattern.split("|"):
            pat = re.compile(
                rf"{re.escape(label)}\s+(?:.*?)\s+\d+\s*/\s*(\d+)",
                re.IGNORECASE,
            )
            m = pat.search(content)
            if m:
                return int(m.group(1))
        return None


class QuartusRuntimeParser:
    STAGE_PATTERNS = {
        "synthesis": [
            re.compile(r"Info: .*Synthesis.*?elapsed\s+time.*?(\d+):(\d+):(\d+)", re.IGNORECASE),
        ],
        "fitter": [
            re.compile(r"Info: .*Fitter.*?elapsed\s+time.*?(\d+):(\d+):(\d+)", re.IGNORECASE),
        ],
        "assembler": [
            re.compile(r"Info: .*Assembler.*?elapsed\s+time.*?(\d+):(\d+):(\d+)", re.IGNORECASE),
        ],
        "timing_analyzer": [
            re.compile(r"Info: .*TimeQuest.*?elapsed\s+time.*?(\d+):(\d+):(\d+)", re.IGNORECASE),
            re.compile(r"Info: .*Timing Analyzer.*?elapsed\s+time.*?(\d+):(\d+):(\d+)", re.IGNORECASE),
        ],
    }

    def parse(self, content: str, source_file: str = "") -> ParseResult[RuntimeResult]:
        errors: list[str] = []
        warnings: list[str] = []

        if not content.strip():
            return ParseResult(success=False, errors=["empty log file"])

        try:
            synth_dur = self._extract_stage_duration(content, "synthesis")
            fitter_dur = self._extract_stage_duration(content, "fitter")
            asm_dur = self._extract_stage_duration(content, "assembler")
            ta_dur = self._extract_stage_duration(content, "timing_analyzer")

            impl_dur = None
            if fitter_dur is not None:
                impl_dur = fitter_dur + (asm_dur or 0) + (ta_dur or 0)

            total = None
            total_pattern = re.compile(
                r"Total\s+compilation\s+time.*?(\d+):(\d+):(\d+)",
                re.IGNORECASE,
            )
            m = total_pattern.search(content)
            if m:
                total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            elif synth_dur and impl_dur:
                total = synth_dur + impl_dur

            if synth_dur is None and impl_dur is None and total is None:
                return ParseResult(success=False, errors=["no runtime data found in log"])

            return ParseResult(
                success=True,
                data=RuntimeResult(
                    synthesis_duration=synth_dur,
                    implementation_duration=impl_dur,
                    bitstream_duration=asm_dur,
                    total_runtime=total,
                ),
                warnings=warnings,
            )
        except Exception as e:
            logger.error("quartus_runtime_parse_failed", source=source_file, error=str(e))
            return ParseResult(success=False, errors=[f"parse error: {e}"])

    def _extract_stage_duration(self, content: str, stage: str) -> float | None:
        patterns = self.STAGE_PATTERNS.get(stage, [])
        for pat in patterns:
            m = pat.search(content)
            if m and len(m.groups()) == 3:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        return None


class QuartusReportParser(ReportParser):
    def __init__(self) -> None:
        self._timing = QuartusTimingParser()
        self._utilization = QuartusUtilizationParser()
        self._runtime = QuartusRuntimeParser()

    def parse_timing(self, content: str, source_file: str = "") -> ParseResult[TimingResult]:
        return self._timing.parse(content, source_file)

    def parse_utilization(self, content: str, source_file: str = "") -> ParseResult[UtilizationResult]:
        return self._utilization.parse(content, source_file)

    def parse_runtime(self, content: str, source_file: str = "") -> ParseResult[RuntimeResult]:
        return self._runtime.parse(content, source_file)


class QuartusProjectDetector:
    REPORT_PATTERNS = {
        "timing": ["*.sta.rpt", "*timing*.rpt", "*sta.rpt"],
        "utilization": ["*.fit.rpt", "*fitter*.rpt", "*resource*.rpt"],
        "log": ["*.log", "quartus.log"],
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
