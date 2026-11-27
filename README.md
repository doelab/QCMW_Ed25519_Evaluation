# QCMW Ed25519 Evaluation Artifacts

This repository provides evaluation artifacts, synthesis constraints, and side-channel analysis scripts for:

> **"First-Order Side-Channel Leakage Suppression in Ed25519 via Quad-Core Wavefront Scheduling"**
> *Microprocessors and Microsystems (Elsevier)*

---

## Directory Layout

```
QCMW_Ed25519_Evaluation/
├── sca_analysis/                     # Side-channel analysis scripts and test vectors
│   ├── tvla_vectors.csv              # Sample fixed-vs-random 255-bit scalar vectors
│   ├── tvla_vectors_sample.csv       # Sample scalar vector log
│   ├── tvla_welch_ttest.py           # Welch's t-test, Sidak thresholds, noncentral-t CIs & trace bootstrap
│   ├── snr_leakage_calc.py           # Class-conditional SNR, attenuation & propagated 95% CIs
│   ├── cpa_simulation.py             # Calibrated binary datapath leakage and MTD simulation
│   └── cpa_results/                  # Generated plots (ASR, classification accuracy, TVLA t-statistic)
├── synthesis_constraints/            # Hardware synthesis and timing constraints
│   ├── nexys_a7_100t.xdc             # Artix-7 pins, 10 MHz test clock, PMOD trigger
│   ├── ultrascale_plus_384mhz.xdc    # UltraScale+ timing closure constraints (T = 2.60 ns)
│   └── pblock_quadcore_floorplan.xdc # Vivado Pblock physical floorplanning for cores 0–3
└── verification_models/              # Functional verification models and test vectors
    ├── ed25519_design_model.py       # Architecture model for wavefront scheduling
    ├── ed25519_ref_djb.py            # Reference Ed25519 implementation (Bernstein et al.)
    ├── sign.input                    # 1,024 official RFC 8032 test vectors
    ├── verify_official.py            # Single-vector verification against official reference
    └── verify_regression.py          # Complete 1,024/1,024 regression test suite
```

---

## Reproduction Commands

### 1. Requirements

Install the required Python packages:

```bash
pip install numpy scipy matplotlib
```

### 2. Functional Verification

Run the regression suite across all 1,024 official RFC 8032 test vectors:

```bash
cd verification_models
python3 verify_regression.py
```

*Expected Output:* `Summary: 1024/1024 passed, 0 failed.`

Test single-vector execution against Bernstein's reference implementation:

```bash
python3 verify_official.py
```

*Expected Output:* `Result: PASS (Y-coordinate match; sign bit differs by Montgomery X-only representation)`

### 3. Leakage SNR and Propagated Intervals

Calculate empirical class-conditional leakage SNR, exact 95% confidence intervals, and architectural noise attenuation:

```bash
cd sca_analysis
python3 snr_leakage_calc.py
```

*Expected Output:*

- QCMW: peak `|t| = 4.39` (95% CI `[2.43, 6.35]`) -> `SNR = 3.85e-04` (`-34.14 dB`, 95% CI `[-39.28, -30.93] dB`)
- Single-core: peak `|t| = 11.16` (95% CI `[9.20, 13.12]`) -> `SNR = 2.49e-03` (`-26.04 dB`, 95% CI `[-27.71, -24.63] dB`)
- Empirical attenuation: **8.10 dB** (`4-core 1/N model: 6.02 dB`, `residual: 2.08 dB`).

### 4. TVLA Welch t-Test, Exact Noncentral-t Confidence Intervals, and Bootstrap Check

Compute the trace-wide Sidak multiple-comparison thresholds over `M = 189,790` samples (`37,958 cycles x 5 samples/cycle`), the exact noncentral-t 95% confidence intervals (`df = 199,998`) at the observed peak sample index `j*`, and a calibrated `B = 2,000` independent within-group trace-resampling check (`n0 = n1 = 100,000` traces/group):

```bash
cd sca_analysis
python3 tvla_welch_ttest.py
```

*Expected Output:*

- Reference threshold: `|t| = 4.50`
- Sidak thresholds: `|t_crit| = 6.56` (`alpha = 1e-5`), `|t_crit| = 5.14` (`alpha = 0.05`)
- QCMW (`N = 100,000/group`, peak `|t| = 4.39`, `SNR = -34.14 dB`):
  - Noncentral-t 95% CI at `j*`: `[2.43, 6.35]` -> SNR `[-39.28, -30.93] dB`
  - Trace bootstrap (`B = 2000`, `seed = 42`): `[2.54, 6.39]` -> SNR `[-38.89, -30.88] dB`
- Single-core baseline (`N = 100,000/group`, peak `|t| = 11.16`, `SNR = -26.04 dB`):
  - Noncentral-t 95% CI at `j*`: `[9.20, 13.12]` -> SNR `[-27.71, -24.63] dB`
  - Trace bootstrap (`B = 2000`, `seed = 42`): `[9.14, 13.11]` -> SNR `[-27.77, -24.64] dB`
- Single-trace classification Wilson 95% CI (`50.73%`, `50,729 / 100,000`): `[50.42%, 51.04%]`

### 5. Calibrated First-Order Leakage and Trace-Averaging Model

Simulate single-bit binary leakage and repeated-trace distinguishability calibrated to the measured 10 MHz Artix-7 noise floor (`sigma = 54.66`, `-34.8 dB` model SNR) targeting scalar bit `k_254` at the coprocessor datapath boundary:

```bash
cd sca_analysis
python3 cpa_simulation.py
```

*Expected Output:*

- Per-trace accuracy: **50.73%** (`50,729 / 100,000`, 0.73 percentage points above chance, 95% Wilson score interval `[50.42%, 51.04%]`).
- Peak `|t|` statistic: **4.39**.
- Minimum Traces to Disclosure (MTD) for `k_254` under repeated identical scalar inputs:
  - **MTD (90% confidence)** ≈ 4,907 traces
  - **MTD (99% confidence)** ≈ 16,169 traces
  - **MTD (99.9% confidence)** ≈ 28,531 traces
- Output plots saved in `sca_analysis/cpa_results/`.

---

## Evaluation Scope and Data Availability

Physical near-field EM measurements were conducted on a Digilent Nexys A7-100T Artix-7 board at 10 MHz (`synthesis_constraints/nexys_a7_100t.xdc`). Timing benchmarks are synthesized separately. High-frequency timing closure targets AMD Virtex UltraScale+ at 384.62 MHz (`synthesis_constraints/ultrascale_plus_384mhz.xdc`, `T = 2.60 ns`, `WNS = 0.00 ns`), with dedicated rectangular Pblocks (`synthesis_constraints/pblock_quadcore_floorplan.xdc`) assigning each CIOS core to non-overlapping DSP columns. Empirical conclusions are restricted to 10 MHz Artix-7 non-specific TVLA attenuation and simulated single-bit datapath distinguishability, and must not be extrapolated as demonstrated physical key-recovery resistance or high-frequency leakage bounds at 384.62 MHz.

**Artifact Availability:**
- **Public (in this repository):** Evaluation datasets, scalar test vectors, Python statistical and simulation pipelines, Vivado constraints, floorplanning scripts, and RFC 8032 functional models.
- **Available on request:** Synthesizable RTL source files, top-level simulation testbenches, and raw oscilloscope binary trace archives (>15 GB) are available from the corresponding author upon reasonable request.
