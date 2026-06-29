# FPGA Build Prediction & ML: Research Report

## 1. Pre-Trained Models for FPGA Build Prediction

### Plunify InTime (Commercial, No Public Weights)
- **URL**: https://www.plunify.com/en/intime/
- **GitHub**: https://github.com/plunify/InTime (scripts only, 3 stars)
- **Model**: Proprietary/closed-source. Uses Naive Bayes, Decision Trees, and other classifiers internally. No pre-trained model weights are published.
- **Capability**: Timing closure prediction via CAD parameter selection. Claims >50% performance increase. Supports Vivado, Quartus, ISE, Libero.
- **Key papers**:
  - "InTime: A Machine Learning Approach for Efficient Selection of FPGA CAD Tool Parameters" (FPGA 2015, cited 57x) — https://dl.acm.org/doi/abs/10.1145/2684746.2689081
  - "Improving Classification Accuracy of a ML Approach for FPGA Timing Closure" (FCCM 2016, cited 24x) — https://ieeexplore.ieee.org/abstract/document/7544751/
  - "Driving Timing Convergence of FPGA Designs through ML and Cloud Computing" (FCCM 2015, cited 47x) — https://ieeexplore.ieee.org/abstract/document/7160055/
- **Note**: They also have a feature called "Agatha" for predicting compilation failure, but limited to prototyping domain only.

### AMD/Xilinx Vivado ML
- **No public pre-trained models from AMD/Xilinx for build prediction.**
- RapidWright (https://github.com/Xilinx/RapidWright, 382 stars) has some ML-related utilities (e.g., `MLEstimator` class in Java docs), but no `ml-estimation-data` directory or released training datasets were found.
- Xilinx has published research on ML-assisted placement/routing but hasn't released models or build-result datasets publicly.

### Intel Quartus ML
- **No public pre-trained models found.** Intel has published some research on Quartus ML optimizations but nothing downloadable.

### HuggingFace
- **7 models** match "FPGA" on HuggingFace as of June 2026:
  - `evan6007/FPGA-LPR` — License plate recognition on FPGA (not build prediction)
  - `williamliao28/high-throughput-fpga-denoising` — Denoising accelerator
  - `jdavidbr/hunyuan-fpga-merged` — 8B model, unclear relevance
  - `TadiGanesh/fpga-power-mode-predictor` — Power mode prediction (repo not found)
  - `arkhe-os/arkhe-os-v176-fpga-noma-federated-zk-calabiyau-torsion` — Unrelated
  - `hakatu/fpga-whale-training` / `fpga-whale-100m` — Unclear
- **None are for FPGA build/timing/runtime prediction.**

### Open-Source FPGA ML on GitHub
- No repositories found matching "FPGA timing prediction ML" or "FPGA utilization prediction ML" on GitHub.
- No code or model releases from any InTime-related papers.

### Verdict
**There are NO publicly available pre-trained models for FPGA build prediction (timing, runtime, or utilization).** All known production systems (InTime) are commercial with proprietary models. This is a significant gap.

---

## 2. Is Synthetic Data Sufficient for FPGA Build Prediction?

### What "Synthetic" Means in FPGA Context
Synthetic FPGA data = designs generated from benchmark suites (CHStone, MachSuite, Polybench) with directive variations (loop unroll, pipeline, array partition), then synthesized with Vivado/Vitis HLS. This is different from "real" data which comes from production FPGA designs.

### Key Findings

**Pal et al. (2022)** — "Machine Learning for Agile FPGA Design" (Springer, cited 11x)
- Link: https://link.springer.com/chapter/10.1007/978-3-031-13074-8_16
- **Explicitly states**: "the ML model trained on the synthetic benchmark can [work]" but notes limitations from "constraints imposed by the target FPGA device" and that synthetic benchmarks "neglect to consider limitations imposed by finite on-chip resources."
- Models trained on synthetic benchmarks often overestimate performance because synthetic designs lack the interconnect complexity, IP heterogeneity, and real placement/routing challenges of production designs.

**Plunify Blog (2023)** — "Can FPGA Compilation Failures Be Predicted?"
- Link: https://support.plunify.com/en/2023/05/29/can-fpga-compilation-failures-be-predicted/
- **Key caveat**: "Obtaining a sufficiently diverse and comprehensive dataset that represents the entire range of possible scenarios can be a daunting task."
- They **deliberately limited** their "Agatha" model to the prototyping domain only because of data diversity limitations.
- Acknowledges that FPGA design complexity involves "a multitude of interdependent factors."

**Liao et al. (2024)** — "Skip the Benchmark: Generating System-Level HLS Data Using Generative ML" (GLSVLSI 2024, cited 4x)
- Link: https://dl.acm.org/doi/abs/10.1145/3649476.3658738
- Proposes generative ML to create synthetic HLS data, showing that small benchmark-only datasets are insufficient.
- **"datasets targeting only a few FPGA boards and a specific HLS tool may prove insufficient for developing accurate ML"** models.

**Batchelor et al.** — "Towards Synthetic Data Generation for Characterization of FPGAs"
- Link: https://www.grafresearch.com/s/Batchelor-Towards-Synthetic-Data-Generation-P-110.pdf
- Discusses synthetic data for FPGA counterfeit detection. Notes "there is no limit" to characterization data needs.

### Limitations of Synthetic Data for Build Prediction
1. **Design diversity gap**: Benchmarks (CHStone: ~10 designs, MachSuite: ~13, Polybench: ~30) are tiny compared to real production designs
2. **No real timing closure failure modes**: Synthetic designs rarely hit the edge cases that cause real build failures (congestion, routing failures, timing violations from complex interconnect)
3. **Vendor tool version sensitivity**: Build results vary across Vivado/Quartus versions — synthetic data is typically generated with a single version
4. **Device-specific overfitting**: Models trained on synthetic data for one FPGA family generalize poorly to others (Plunify calls this "device over-fit")
5. **Missing real-world RTL patterns**: IP cores, DSP blocks, hard memory interfaces, and multi-clock domain interactions are absent from benchmarks
6. **No distributed build variance**: Real builds exhibit stochastic variation from placement seeds — synthetic datasets often only use 1 seed

### Verdict
**Synthetic data alone is NOT sufficient for robust FPGA build prediction**, especially for timing closure and failure prediction. It works reasonably for HLS resource estimation (LUT/FF/BRAM/DSP count prediction) where the relationship between C-code directives and utilization is more deterministic. But for timing, routing congestion, and runtime prediction, real build data is essential.

---

## 3. Real Datasets for FPGA Builds

### HLSDataset (UT Austin, 2023) — THE most relevant dataset
- **Paper**: "HLSDataset: Open-Source Dataset for ML-Assisted FPGA Design using High Level Synthesis" (Zhigang Wei, Aman Arora, Ruihao Li, Lizy K. John)
- **arXiv**: https://arxiv.org/abs/2302.10977
- **IEEE**: https://ieeexplore.ieee.org/abstract/document/10265706/ (cited 30x)
- **Size**: ~9,000 Verilog samples per FPGA type
- **Sources**: Polybench, Machsuite, CHStone, Rosetta benchmarks
- **Directives**: Loop unroll, loop pipeline, array partition
- **Contents**: HLS C source → Vitis HLS synthesis → Vivado implementation results (utilization, power, timing)
- **GitHub**: Referenced in the paper as publicly available (search for "wei" + "HLSDataset" on GitHub)
- **Limitations**: HLS-only (not RTL builds), single FPGA family per dataset

### HLSFactory (Georgia Tech / Sharc Lab, 2024) — Framework for building datasets
- **Paper**: "HLSFactory: A Framework Empowering High-Level Synthesis Datasets for Machine Learning and Beyond" (MLCAD 2024, cited 21x)
- **GitHub**: https://github.com/sharc-lab/HLSFactory (53 stars, 55 forks)
- **Built-in Design Sources**: PolyBench, MachSuite, CHStone, Rosetta (partial), PP4FPGA, Vitis HLS Examples, FlowGNN, and selected accelerator kernels
- **Supported Flows**: Vitis HLS → Vivado, Intel HLS → Quartus
- **Can generate**: Full synthesis + implementation results with custom directive sampling
- **Provides**: Full framework to run your own flows and collect build data
- **License**: AGPL-3.0 (code), CC-BY-SA-4.0 (data)
- **Installable**: `pip install git+https://github.com/sharc-lab/HLSFactory`

### HLStrans (2025) — Newer dataset
- **Paper**: "HLStrans: Dataset for C-to-HLS Hardware Code Synthesis" (cited 3x)
- **arXiv**: https://arxiv.org/abs/2507.04315
- Focuses on C-to-HLS code translation; builds on HLSDataset

### XPNet / Cross-FPGA Power Prediction (2025)
- **Paper**: "XPNet: Cross-FPGA Power Prediction from High Level Language Code" (ICCAD 2025)
- Uses HLSDataset and provides scripts to extend it to cover more FPGAs
- Transfer learning approach for cross-device generalization

### AvistoTelecom/dataset_designs_fpga (HuggingFace)
- **URL**: https://huggingface.co/datasets/AvistoTelecom/dataset_designs_fpga
- **Status**: Currently EMPTY (2.46 kB, no data uploaded). Appears to be a placeholder.

### ISPD 2016 Contest Dataset (Routing/Placement)
- Used by multiple FPGA routability prediction papers
- Contains placement instances for FPGA routing benchmarks
- Access via ISPD contest archives

### Dovado (Open-source DSE framework, 2021)
- **Paper**: "Dovado: An Open-Source Design Space Exploration Framework" (FCCM 2021, cited 11x)
- Caches Vivado build results, but not a standalone dataset

### Benchmark Suites (Source Code Only — No Build Results)

| Benchmark | URL | Designs | Stars | Notes |
|-----------|-----|---------|-------|-------|
| **CHStone** | Multiple mirrors | ~10 C benchmarks | N/A | HLS benchmark suite, originally from Nara Institute |
| **MachSuite** | https://github.com/breagen/MachSuite | 13 benchmarks × variants | 138 | HLS-focused, BSD license |
| **PolyBench** | Multiple sources | ~30 polyhedral benchmarks | N/A | Adapted for HLS |
| **Rosetta** | Various repos | ML/DL/Signal processing kernels | N/A | Partially integrated into HLSFactory |

> **Important**: These benchmark suites provide **source code only**. You must run actual builds yourself to generate build-result datasets.

### ML4Accel-Dataset (UT Austin)
- Could NOT find a publicly available dataset under this exact name. The HLSDataset (from the same group at UT Austin / Lizy John's lab) may be what was referred to.

### RapidWright ml-estimation-data
- **Does NOT exist as a separate repository or directory** within the RapidWright project as of June 2026. RapidWright has ML-related Java classes referenced in docs, but no released training data.

### EDA ML Datasets (Non-FPGA)
- **DAC/ISPD Contest Data**: Some placement/routing contest data exists but typically for ASIC, not FPGA
- **TensorRT/DNN-based EDA**: No specific FPGA build-result datasets found
- There are no FPGA equivalents of datasets like "DREAMPlace" or "OpenABC" (which are ASIC-focused)

---

## 4. FPGA DSE Datasets with Actual Build Results

### Existing DSE Papers and Their Data Practices

| Paper | Venue | Cited | Data Availability | Build Tool | Designs |
|-------|-------|-------|-------------------|------------|---------|
| Zhong et al. "DSE of FPGA accelerators with multi-level parallelism" | DATE 2017 | 97 | **Not public** | Vivado HLS | Custom |
| Wang & Schafer "Learning from the Past: Efficient HLS DSE for FPGAs" | TODAES 2022 | 28 | **Large database mentioned but not public** | Vivado HLS | Multiple HLS benchmarks |
| Rashid & Schafer "Fast and Inexpensive HLS DSE" | ICCAD 2023 | 10 | **Not public** | Intel HLS + Vivado | Benchmarks |
| Yu et al. "Chimera: Hybrid ML-driven Multi-objective DSE" | IDEAL 2021 | 20 | **Not public** | Vivado HLS | HLS benchmarks |
| Paletti et al. "Dovado: Open-source DSE framework" | FPL 2021 | 11 | Framework available, data only via running Vivado | Vivado | Custom |
| Goswami & Bhatia "Application of ML in FPGA EDA Tool Development" | IEEE Access 2023 | 29 | **Not public** | Xilinx tools | Multiple |

### Verdict on DSE Datasets
**No publicly available FPGA DSE dataset with actual Vivado/Quartus post-implementation build results (timing, utilization, runtime) was found.** Every paper generates its own private dataset by running builds on HLS benchmarks with directive permutations. HLSFactory and HLSDataset are the closest things but focus on HLS-level metrics.

---

## 5. What Published Papers Use for Training Data

### Summary of Training Data Sources (from literature survey)

| Approach | Typical Training Data | Size | Public? |
|----------|----------------------|------|---------|
| **InTime/Plunify** (2015-2016) | Real customer build results + cloud runs | Tens to hundreds of builds per design | No (proprietary) |
| **Timing delay prediction** (Martin et al., 2021) | FPGA placement features from benchmarks | Moderate | No |
| **Routability prediction** (Gunter & Wilton, 2023-2025) | Custom generated netlists + ISPD 2016 data | ~1000 placement instances | Partially |
| **HLS resource estimation** (Various) | HLSDataset / HLSFactory-generated data | ~9000 samples per FPGA | **Yes** (HLSDataset) |
| **HLS DSE** (Schafer group, 2022-2023) | Private databases from years of DSE runs | Very large (claimed) | No |
| **Congestion prediction** (Zhao et al., various Chinese groups) | Custom datasets from benchmark runs | ~1000 designs | No |
| **Power estimation** (UT Austin group, 2023-2025) | HLSDataset + extensions | ~9000+ | Partially |
| **Compilation failure** (Plunify "Agatha", 2023) | Plunify cloud build history | Undisclosed | No |

### Common Pattern
1. Most papers run **their own builds** using Vivado/Quartus on benchmark suites
2. They vary **directives/pragmas** to create design point diversity
3. Typical dataset: **100-10,000 design points** across **5-30 benchmark designs**
4. Build time for dataset generation: **days to weeks** of compute
5. Data is almost **never published** alongside the paper
6. The **HLSDataset** and **HLSFactory** are the only two projects that explicitly create and share ML-ready FPGA build data

### Key Survey Paper
**Biscontini, Popovici, Temko (2024)** — "Machine Learning for FPGA Electronic Design Automation" (IEEE Access, cited 13x)
- Link: https://ieeexplore.ieee.org/abstract/document/10776975/
- Comprehensive survey covering ML for routing congestion, timing, power, placement, and HLS
- Reviews existing datasets and their limitations
- Notes the **scarcity of large-scale public datasets** as a major bottleneck

---

## Key Takeaways

1. **No pre-trained models exist publicly** for FPGA build prediction. InTime is commercial; everything else is paper-only with no released models.

2. **Synthetic data from benchmarks is insufficient** for robust timing/routing/failure prediction. It works for HLS resource estimation. Real production design data is needed but hard to obtain (IP, confidentiality).

3. **Only two real datasets exist**: HLSDataset (~9K samples, HLS-level) and HLSFactory (framework + built-in designs). Neither covers RTL-level Vivado/Quartus full implementation builds at scale.

4. **Zero public DSE datasets** with actual post-implementation build results (WNS/TNS, utilization, runtime) were found.

5. **Papers generate their own private data** — typically by running builds on 5-30 benchmarks with directive variations (100-10K design points). This data is almost never shared.

6. **The biggest gap** is the lack of RTL-level build prediction datasets with real timing closure, routing congestion, and runtime data from actual industrial designs.
