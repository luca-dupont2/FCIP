from __future__ import annotations

from fcip_parsers.base import ReportParser
from fcip_parsers.vivado import VivadoReportParser
from fcip_parsers.quartus import QuartusReportParser

_PARSERS: dict[str, type[ReportParser]] = {
    "vivado": VivadoReportParser,
    "quartus": QuartusReportParser,
}


def get_parser(tool: str) -> ReportParser:
    cls = _PARSERS.get(tool.lower())
    if cls is None:
        raise ValueError(f"no parser registered for tool: {tool!r}. available: {list(_PARSERS.keys())}")
    return cls()


def register_parser(tool: str, parser_cls: type[ReportParser]) -> None:
    _PARSERS[tool.lower()] = parser_cls


def available_parsers() -> list[str]:
    return list(_PARSERS.keys())
