from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np


DEVICES = [
    "xcvu9p-flgb2104-2-e",
    "xcvu3p-ffvc1517-2-e",
    "xcku060-ffva1156-2-e",
    "5CEFA7F31C6",
    "10AS066N3F40E2SG",
]

DEVICE_BASE_WNS = {
    "xcvu9p-flgb2104-2-e": 0.5,
    "xcvu3p-ffvc1517-2-e": 0.3,
    "xcku060-ffva1156-2-e": 0.1,
    "5CEFA7F31C6": 0.8,
    "10AS066N3F40E2SG": 0.4,
}

DEVICE_BASE_RUNTIME = {
    "xcvu9p-flgb2104-2-e": 5400,
    "xcvu3p-ffvc1517-2-e": 3600,
    "xcku060-ffva1156-2-e": 2700,
    "5CEFA7F31C6": 1800,
    "10AS066N3F40E2SG": 3200,
}


@dataclass
class SyntheticExperiment:
    device: str
    lut: int
    lut_available: int
    ff: int
    ff_available: int
    bram: int
    bram_available: int
    dsp: int
    dsp_available: int
    seed: int
    wns: float
    tns: float
    total_runtime: float
    strategy: str
    retiming: bool
    phys_opt: bool
    timing_success: bool


class SyntheticExperimentGenerator:
    def __init__(
        self,
        n_samples: int = 2000,
        devices: list[str] | None = None,
        seed_range: tuple[int, int] = (1, 100),
        utilization_range: tuple[float, float] = (0.1, 0.95),
        base_seed: int = 42,
    ) -> None:
        self.n_samples = n_samples
        self.devices = devices or DEVICES
        self.seed_range = seed_range
        self.utilization_range = utilization_range
        self.rng = np.random.default_rng(base_seed)

    def generate(self) -> list[SyntheticExperiment]:
        experiments: list[SyntheticExperiment] = []
        for _ in range(self.n_samples):
            device = self.rng.choice(self.devices)
            util = self.rng.uniform(*self.utilization_range)
            seed = int(self.rng.integers(self.seed_range[0], self.seed_range[1] + 1))

            lut_avail = self.rng.integers(100000, 500000)
            ff_avail = lut_avail * 2
            bram_avail = self.rng.integers(200, 2000)
            dsp_avail = self.rng.integers(100, 2000)

            lut = int(lut_avail * util)
            ff = int(ff_avail * util * self.rng.uniform(0.5, 1.5))
            bram = int(bram_avail * util * self.rng.uniform(0.3, 1.0))
            dsp = int(dsp_avail * util * self.rng.uniform(0.1, 0.5))

            base_wns = DEVICE_BASE_WNS.get(device, 0.3)
            util_penalty = (util - 0.5) * 4.0
            seed_effect = self.rng.normal(0, 0.3)
            noise = self.rng.normal(0, 0.2)
            wns = base_wns - util_penalty + seed_effect + noise

            retiming = bool(self.rng.integers(0, 2))
            phys_opt = bool(self.rng.integers(0, 2))
            if retiming:
                wns += self.rng.uniform(0, 0.3)
            if phys_opt:
                wns += self.rng.uniform(0, 0.2)

            strategies = ["default", "Performance_Explore", "Area_Explore", "Power_Explore"]
            strategy = str(self.rng.choice(strategies))
            if strategy == "Performance_Explore":
                wns += self.rng.uniform(0, 0.4)
            elif strategy == "Area_Explore":
                wns -= self.rng.uniform(0, 0.2)

            tns = wns * self.rng.uniform(1, 10) if wns < 0 else 0.0

            base_runtime = DEVICE_BASE_RUNTIME.get(device, 2700)
            runtime_factor = util * 2.0 + 1.0
            if strategy != "default":
                runtime_factor *= 1.1
            total_runtime = max(300, base_runtime * runtime_factor + self.rng.normal(0, 600))

            timing_success = wns >= 0

            experiments.append(SyntheticExperiment(
                device=device,
                lut=lut,
                lut_available=int(lut_avail),
                ff=ff,
                ff_available=int(ff_avail),
                bram=bram,
                bram_available=int(bram_avail),
                dsp=dsp,
                dsp_available=int(dsp_avail),
                seed=seed,
                wns=round(wns, 4),
                tns=round(tns, 4),
                total_runtime=round(total_runtime, 1),
                strategy=strategy,
                retiming=retiming,
                phys_opt=phys_opt,
                timing_success=bool(timing_success),
            ))

        return experiments
