from __future__ import annotations

from dataclasses import dataclass, field

from fcip_recommender.engine import RecommendationEngine
from fcip_recommender.rules import RULES, Rule
from fcip_recommender.types import RecommendationCategory, RecommendationPriority


@dataclass
class MockReport:
    wns: float | None = None
    tns: float | None = None
    failing_paths: int | None = None
    lut: int | None = None
    lut_available: int | None = None
    ff: int | None = None
    ff_available: int | None = None
    bram: int | None = None
    bram_available: int | None = None
    dsp: int | None = None
    dsp_available: int | None = None
    synthesis_duration: float | None = None
    total_runtime: float | None = None


@dataclass
class MockExperiment:
    compile_options: dict = field(default_factory=dict)


class TestRecommendationEngine:
    def setup_method(self):
        self.engine = RecommendationEngine()

    def test_no_recommendations_for_healthy_build(self):
        exp = MockExperiment(compile_options={"retiming": True, "phys_opt": True})
        rpt = MockReport(wns=0.5, tns=0.0, failing_paths=0, lut=1000, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100,
                         total_runtime=600)
        recs = self.engine.evaluate(exp, [rpt])
        assert len(recs) == 0

    def test_r01_high_lut_with_timing_violation(self):
        exp = MockExperiment()
        rpt = MockReport(wns=-1.5, lut=8500, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R01" in rule_ids

    def test_r02_high_bram(self):
        exp = MockExperiment()
        rpt = MockReport(wns=0.5, lut=100, lut_available=10000,
                         bram=90, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R02" in rule_ids

    def test_r03_high_dsp(self):
        exp = MockExperiment()
        rpt = MockReport(wns=0.5, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=95, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R03" in rule_ids

    def test_r05_near_timing_closure(self):
        exp = MockExperiment(compile_options={"retiming": True, "phys_opt": True})
        rpt = MockReport(wns=-0.2, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R05" in rule_ids

    def test_r06_severe_timing_violation(self):
        exp = MockExperiment(compile_options={"retiming": True, "phys_opt": True})
        rpt = MockReport(wns=-3.0, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R06" in rule_ids

    def test_r07_long_runtime(self):
        exp = MockExperiment(compile_options={"retiming": True, "phys_opt": True})
        rpt = MockReport(wns=0.5, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100,
                         total_runtime=20000)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R07" in rule_ids

    def test_r09_retiming_not_enabled(self):
        exp = MockExperiment(compile_options={"retiming": False, "phys_opt": True})
        rpt = MockReport(wns=-0.5, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R09" in rule_ids

    def test_r10_phys_opt_not_enabled(self):
        exp = MockExperiment(compile_options={"retiming": True, "phys_opt": False})
        rpt = MockReport(wns=-0.5, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R10" in rule_ids

    def test_r12_many_failing_paths(self):
        exp = MockExperiment(compile_options={"retiming": True, "phys_opt": True})
        rpt = MockReport(wns=-0.5, failing_paths=200, lut=100, lut_available=10000,
                         bram=10, bram_available=100, dsp=5, dsp_available=100)
        recs = self.engine.evaluate(exp, [rpt])
        rule_ids = [r.rule_name for r in recs]
        assert "R12" in rule_ids

    def test_empty_report_no_crash(self):
        exp = MockExperiment()
        recs = self.engine.evaluate(exp, [])
        assert isinstance(recs, list)

    def test_none_report_no_crash(self):
        exp = MockExperiment()
        recs = self.engine.evaluate(exp, None)
        assert isinstance(recs, list)

    def test_recommendations_sorted_by_priority(self):
        exp = MockExperiment()
        rpt = MockReport(wns=-3.0, lut=8500, lut_available=10000,
                         bram=10, bram_available=100, dsp=95, dsp_available=100,
                         failing_paths=200, total_runtime=20000)
        recs = self.engine.evaluate(exp, [rpt])
        priorities = [r.priority for r in recs]
        for i in range(len(priorities) - 1):
            assert priorities[i].value <= priorities[i + 1].value or \
                   priorities[i] == RecommendationPriority.HIGH

    def test_custom_rules(self):
        custom = Rule(
            rule_id="CUSTOM_01",
            condition=lambda exp, rpt, ctx: True,
            message="Custom rule fired",
            category=RecommendationCategory.STRATEGY,
            priority=RecommendationPriority.LOW,
            confidence=0.5,
        )
        engine = RecommendationEngine(rules=[custom])
        exp = MockExperiment()
        rpt = MockReport(wns=0.5)
        recs = engine.evaluate(exp, [rpt])
        assert len(recs) == 1
        assert recs[0].rule_name == "CUSTOM_01"

    def test_all_12_rules_exist(self):
        assert len(RULES) == 12
