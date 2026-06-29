"""Generate synthetic experiment data and insert into database."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fcip_shared.database import async_session_factory
from fcip_shared.models.project import Project
from fcip_shared.models.experiment import Experiment
from fcip_shared.models.report import Report
from fcip_predictor.generator import SyntheticExperimentGenerator


async def main(n_samples: int = 2000) -> None:
    gen = SyntheticExperimentGenerator(n_samples=n_samples)
    data = gen.generate()

    async with async_session_factory() as session:
        project = Project(
            id=uuid.uuid4(),
            name="synthetic_benchmark",
            path="/synthetic",
            description="Synthetic benchmark data for testing",
        )
        session.add(project)
        await session.flush()

        print(f"Created project: {project.name} ({project.id})")
        print(f"Generating {len(data)} synthetic experiments...")

        for i, s in enumerate(data):
            exp = Experiment(
                id=uuid.uuid4(),
                project_id=project.id,
                name=f"synth_run_{i:04d}",
                tool="vivado",
                device=s.device,
                seed=s.seed,
                status="success" if s.timing_success else "failed",
                source="synthetic",
                compile_options={
                    "strategy": s.strategy,
                    "retiming": s.retiming,
                    "phys_opt": s.phys_opt,
                },
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            session.add(exp)
            await session.flush()

            report = Report(
                id=uuid.uuid4(),
                experiment_id=exp.id,
                report_type="combined",
                wns=s.wns,
                tns=s.tns,
                lut=s.lut,
                lut_available=s.lut_available,
                ff=s.ff,
                ff_available=s.ff_available,
                bram=s.bram,
                bram_available=s.bram_available,
                dsp=s.dsp,
                dsp_available=s.dsp_available,
                io_used=0,
                io_available=520,
                synthesis_duration=s.total_runtime * 0.4 if s.total_runtime else None,
                implementation_duration=s.total_runtime * 0.5 if s.total_runtime else None,
                bitstream_duration=s.total_runtime * 0.1 if s.total_runtime else None,
                total_runtime=s.total_runtime,
            )
            session.add(report)

            if (i + 1) % 100 == 0:
                await session.flush()
                print(f"  {i + 1}/{len(data)} experiments inserted")

        await session.commit()
        print(f"Done! Inserted {len(data)} experiments.")


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    asyncio.run(main(n))
