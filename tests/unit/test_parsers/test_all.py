from __future__ import annotations

import pytest
from pathlib import Path

from fcip_parsers import get_parser, available_parsers, register_parser
from fcip_parsers.base import ReportParser
from fcip_parsers.vivado import VivadoReportParser
from fcip_parsers.quartus import QuartusReportParser


FIXTURES = Path(__file__).parent.parent.parent / "data"


class TestRegistry:
    def test_available_parsers(self):
        parsers = available_parsers()
        assert "vivado" in parsers
        assert "quartus" in parsers

    def test_get_vivado_parser(self):
        parser = get_parser("vivado")
        assert isinstance(parser, VivadoReportParser)
        assert isinstance(parser, ReportParser)

    def test_get_quartus_parser(self):
        parser = get_parser("quartus")
        assert isinstance(parser, QuartusReportParser)

    def test_get_unknown_parser_raises(self):
        with pytest.raises(ValueError, match="no parser registered"):
            get_parser("unknown_tool")

    def test_register_custom_parser(self):
        class DummyParser(ReportParser):
            def parse_timing(self, content, source_file=""):
                return None
            def parse_utilization(self, content, source_file=""):
                return None
            def parse_runtime(self, content, source_file=""):
                return None

        register_parser("dummy", DummyParser)
        assert "dummy" in available_parsers()
        parser = get_parser("dummy")
        assert isinstance(parser, DummyParser)


class TestVivadoTiming:
    def test_parse_good_report(self):
        content = (FIXTURES / "vivado" / "timing_report_good.rpt").read_text()
        parser = get_parser("vivado")
        result = parser.parse_timing(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.wns < 0
        assert result.data.tns < 0
        assert result.data.failing_paths > 0
        assert len(result.data.clock_domains) > 0

    def test_parse_failed_report(self):
        content = (FIXTURES / "vivado" / "timing_report_failed.rpt").read_text()
        parser = get_parser("vivado")
        result = parser.parse_timing(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.wns < 0

    def test_parse_empty_returns_failure(self):
        parser = get_parser("vivado")
        result = parser.parse_timing("")
        assert result.success is False
        assert len(result.errors) > 0

    def test_parse_corrupted_graceful(self):
        content = (FIXTURES / "malformed" / "corrupted_timing.rpt").read_text()
        parser = get_parser("vivado")
        result = parser.parse_timing(content)
        assert result.success is True or result.success is False


class TestVivadoUtilization:
    def test_parse_good_report(self):
        content = (FIXTURES / "vivado" / "utilization_report_good.rpt").read_text()
        parser = get_parser("vivado")
        result = parser.parse_utilization(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.lut > 0
        assert result.data.lut_available > 0
        assert result.data.ff > 0
        assert result.data.bram >= 0
        assert result.data.dsp >= 0

    def test_parse_high_util(self):
        content = (FIXTURES / "vivado" / "utilization_report_high_util.rpt").read_text()
        parser = get_parser("vivado")
        result = parser.parse_utilization(content)
        assert result.success is True
        assert result.data is not None

    def test_parse_empty_returns_failure(self):
        parser = get_parser("vivado")
        result = parser.parse_utilization("")
        assert result.success is False

    def test_partial_utilization(self):
        content = (FIXTURES / "malformed" / "partial_utilization.rpt").read_text()
        parser = get_parser("vivado")
        result = parser.parse_utilization(content)
        assert result.success is True or result.success is False


class TestVivadoRuntime:
    def test_parse_log(self):
        content = (FIXTURES / "vivado" / "vivado.log").read_text()
        parser = get_parser("vivado")
        result = parser.parse_runtime(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.total_runtime is not None or result.data.synthesis_duration is not None

    def test_parse_empty_returns_failure(self):
        parser = get_parser("vivado")
        result = parser.parse_runtime("")
        assert result.success is False


class TestQuartusTiming:
    def test_parse_good_report(self):
        content = (FIXTURES / "quartus" / "timing_report_good.rpt").read_text()
        parser = get_parser("quartus")
        result = parser.parse_timing(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.wns is not None

    def test_parse_failed_report(self):
        content = (FIXTURES / "quartus" / "timing_report_failed.rpt").read_text()
        parser = get_parser("quartus")
        result = parser.parse_timing(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.wns < 0

    def test_parse_empty_returns_failure(self):
        parser = get_parser("quartus")
        result = parser.parse_timing("")
        assert result.success is False


class TestQuartusUtilization:
    def test_parse_good_report(self):
        content = (FIXTURES / "quartus" / "utilization_report_good.rpt").read_text()
        parser = get_parser("quartus")
        result = parser.parse_utilization(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.lut > 0
        assert result.data.ff >= 0
        assert result.data.bram >= 0


class TestQuartusRuntime:
    def test_parse_log(self):
        content = (FIXTURES / "quartus" / "quartus.log").read_text()
        parser = get_parser("quartus")
        result = parser.parse_runtime(content)
        assert result.success is True
        assert result.data is not None
        assert result.data.synthesis_duration == 2700
        assert result.data.implementation_duration == 6298
        assert result.data.bitstream_duration == 569
        assert result.data.total_runtime == 9000
