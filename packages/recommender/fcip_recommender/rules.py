from __future__ import annotations

from typing import Callable

from fcip_recommender.types import Recommendation, RecommendationCategory, RecommendationPriority


class Rule:
    def __init__(
        self,
        rule_id: str,
        condition: Callable,
        message: str,
        category: RecommendationCategory,
        priority: RecommendationPriority,
        confidence: float = 0.8,
    ) -> None:
        self.rule_id = rule_id
        self.condition = condition
        self.message = message
        self.category = category
        self.priority = priority
        self.confidence = confidence

    def evaluate(self, experiment, report, project_experiments=None) -> Recommendation | None:
        try:
            if self.condition(experiment, report, project_experiments):
                return Recommendation(
                    rule_name=self.rule_id,
                    category=self.category,
                    priority=self.priority,
                    message=self.message,
                    confidence=self.confidence,
                )
        except Exception:
            pass
        return None


def _lut_pct(report) -> float:
    if report and report.lut and report.lut_available and report.lut_available > 0:
        return report.lut / report.lut_available
    return 0.0


def _bram_pct(report) -> float:
    if report and report.bram and report.bram_available and report.bram_available > 0:
        return report.bram / report.bram_available
    return 0.0


def _dsp_pct(report) -> float:
    if report and report.dsp and report.dsp_available and report.dsp_available > 0:
        return report.dsp / report.dsp_available
    return 0.0


def _wns(report) -> float:
    return report.wns if report and report.wns is not None else 0.0


def _failing_paths(report) -> int:
    return report.failing_paths if report and report.failing_paths is not None else 0


def _total_runtime(report) -> float:
    return report.total_runtime if report and report.total_runtime is not None else 0.0


def _synth_ratio(report) -> float:
    if report and report.synthesis_duration and report.total_runtime and report.total_runtime > 0:
        return report.synthesis_duration / report.total_runtime
    return 0.0


def _seed_variance(project_experiments) -> float:
    if not project_experiments or len(project_experiments) < 2:
        return 0.0
    import statistics
    wns_vals = []
    for exp in project_experiments:
        for rpt in exp.reports:
            if rpt and rpt.wns is not None:
                wns_vals.append(rpt.wns)
    if len(wns_vals) < 2:
        return 0.0
    try:
        return statistics.stdev(wns_vals)
    except Exception:
        return 0.0


def _compile_option(experiment, key: str) -> any:
    if experiment and experiment.compile_options:
        return experiment.compile_options.get(key)
    return None


RULES: list[Rule] = [
    Rule(
        rule_id="R01",
        condition=lambda exp, rpt, ctx: _lut_pct(rpt) > 0.80 and _wns(rpt) < -1.0,
        message="High LUT utilization with timing violation. Consider floorplanning or RTL optimization.",
        category=RecommendationCategory.UTILIZATION,
        priority=RecommendationPriority.HIGH,
        confidence=0.85,
    ),
    Rule(
        rule_id="R02",
        condition=lambda exp, rpt, ctx: _bram_pct(rpt) > 0.85,
        message="BRAM utilization exceeds 85%. Consider using distributed RAM for small buffers or optimizing BRAM packing.",
        category=RecommendationCategory.UTILIZATION,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.80,
    ),
    Rule(
        rule_id="R03",
        condition=lambda exp, rpt, ctx: _dsp_pct(rpt) > 0.90,
        message="DSP utilization near limit. Consider DSP pipelining or replacing with LUT-based arithmetic.",
        category=RecommendationCategory.UTILIZATION,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.80,
    ),
    Rule(
        rule_id="R04",
        condition=lambda exp, rpt, ctx: _seed_variance(ctx) > 0.5,
        message="WNS varies significantly across seeds. A seed sweep is recommended to find optimal seed.",
        category=RecommendationCategory.TIMING,
        priority=RecommendationPriority.HIGH,
        confidence=0.75,
    ),
    Rule(
        rule_id="R05",
        condition=lambda exp, rpt, ctx: -0.5 <= _wns(rpt) < 0.0,
        message="WNS close to timing closure. Retiming or physical optimization may close timing.",
        category=RecommendationCategory.TIMING,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.80,
    ),
    Rule(
        rule_id="R06",
        condition=lambda exp, rpt, ctx: _wns(rpt) < -2.0,
        message="Severe timing violation. Fundamental architectural changes or pipeline restructuring needed.",
        category=RecommendationCategory.TIMING,
        priority=RecommendationPriority.HIGH,
        confidence=0.90,
    ),
    Rule(
        rule_id="R07",
        condition=lambda exp, rpt, ctx: _total_runtime(rpt) > 14400,
        message="Compile duration exceeds 4 hours. Consider incremental compile for localized changes.",
        category=RecommendationCategory.RUNTIME,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.80,
    ),
    Rule(
        rule_id="R08",
        condition=lambda exp, rpt, ctx: _synth_ratio(rpt) > 0.6,
        message="Synthesis dominates compile time. Consider hierarchical synthesis or RTL optimization.",
        category=RecommendationCategory.RUNTIME,
        priority=RecommendationPriority.LOW,
        confidence=0.70,
    ),
    Rule(
        rule_id="R09",
        condition=lambda exp, rpt, ctx: not _compile_option(exp, "retiming") and _wns(rpt) < 0,
        message="Retiming is not enabled. Historical data suggests it improves WNS for this device family.",
        category=RecommendationCategory.STRATEGY,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.75,
    ),
    Rule(
        rule_id="R10",
        condition=lambda exp, rpt, ctx: not _compile_option(exp, "phys_opt") and _wns(rpt) < -0.3,
        message="Physical optimization is disabled. Enabling it may improve timing closure probability.",
        category=RecommendationCategory.STRATEGY,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.75,
    ),
    Rule(
        rule_id="R11",
        condition=lambda exp, rpt, ctx: ctx is not None and len(ctx) > 1 and not _compile_option(exp, "incremental"),
        message="A prior successful build exists. Incremental compile can reduce runtime significantly.",
        category=RecommendationCategory.STRATEGY,
        priority=RecommendationPriority.MEDIUM,
        confidence=0.70,
    ),
    Rule(
        rule_id="R12",
        condition=lambda exp, rpt, ctx: _failing_paths(rpt) > 100,
        message="Large number of failing paths. Consider multi-corner multi-constraint analysis.",
        category=RecommendationCategory.TIMING,
        priority=RecommendationPriority.HIGH,
        confidence=0.85,
    ),
]
