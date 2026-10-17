# QCMW Ed25519 Evaluation Artifacts

This repository provides evaluation artifacts, synthesis constraints, and side-channel analysis scripts for:

> **"First-Order Side-Channel Leakage Suppression in Ed25519 via Quad-Core Wavefront Scheduling"**
> *Microprocessors and Microsystems (Elsevier)*

---

## Directory Layout

```
QCMW_Ed25519_Evaluation_Artifacts/
├── sca_analysis/                     # Side-channel analysis scripts and test vectors
│   ├── tvla_vectors.csv              # Fixed-vs-random 255-bit scalar vectors
│   ├── tvla_vectors_sample.csv       # Sample scalar vector log
│   ├── tvla_welch_ttest.py           # Point-wise Welch's t-test with Mini-p / Sidak correction
│   ├── snr_leakage_calc.py           # Class-conditional SNR and multi-core attenuation
│   ├── cpa_simulation.py             # Calibrated CPA attack and MTD simulation
│   └── cpa_results/                  # Generated plots (ASR, correlation, TVLA t-statistic)
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

*Expected Output:* `Result: PASS (exact 32-byte match)`

### 3. Leakage SNR Calculation

Calculate empirical class-conditional leakage SNR and architectural noise attenuation:

```bash
cd sca_analysis
python3 snr_leakage_calc.py
```

*Expected Output:*

- QCMW: peak `|t| = 4.39` → `SNR = 3.85 × 10⁻⁴` (-34.14 dB, 95% bootstrap CI [-34.57, -33.75] dB)
- Single-core: peak `|t| = 11.16` → `SNR = 2.49 × 10⁻³` (-26.04 dB)
- Empirical attenuation: **8.10 dB** (independent-core heuristic: 6.02 dB, residual margin: 2.08 dB consistent with activity superposition and staggering).

### 4. TVLA Welch t-Test and Bootstrap Confidence Intervals

Run Welch's two-sample t-test against the standard `|t| = 4.5` reference boundary and the trace-wide Sidak multiple-comparison threshold over M = 189,790 samples (37,958 cycles × 5 samples/cycle):

```bash
cd sca_analysis
python3 tvla_welch_ttest.py
```

*Expected Output:*

- Standard reference threshold: `|t| = 4.50`
- Sidak multiple-comparison threshold (α = 10⁻⁵): `|t_crit| = 6.56`
- Measured peak `|t| = 4.39`
- Bootstrap 95% CI for peak `|t|`: [4.18, 4.59] (spanning 4.5, characterizing finite-campaign attenuation)
- Wilson 95% CI for classification accuracy: [50.42%, 51.04%]

### 5. Calibrated First-Order Leakage and Trace-Averaging Model

Simulate binary leakage and trace requirements calibrated to the board noise floor (σ ≈ 55, -34.8 dB model SNR) targeting scalar bit k₂₅₄ at the coprocessor datapath boundary:

```bash
cd sca_analysis
python3 cpa_simulation.py
```

*Expected Output:*

- Per-trace accuracy: **50.73%** (0.73 percentage points above chance, 95% Wilson score interval [50.42%, 51.04%]).
- Peak `|t|` statistic: **4.39**.
- Minimum Traces to Disclosure (MTD) under repeated identical scalar inputs:
  - **MTD (90% confidence)** ≈ 4,907 traces
  - **MTD (99% confidence)** ≈ 16,169 traces
  - **MTD (99.9% confidence)** ≈ 28,531 traces
- Output plots saved in `sca_analysis/cpa_results/`.

---

## Hardware Specifications and Data Availability

Side-channel acquisition was evaluated on a Digilent Nexys A7-100T development board hosting an Artix-7 FPGA (`synthesis_constraints/nexys_a7_100t.xdc`). High-frequency timing closure targets AMD Virtex UltraScale+ at 384.62 MHz (`synthesis_constraints/ultrascale_plus_384mhz.xdc`, T = 2.60 ns, WNS = 0.00 ns). Dedicated rectangular Pblocks (`synthesis_constraints/pblock_quadcore_floorplan.xdc`) isolate each of the four CIOS cores into separate DSP columns without spatial overlap.

**Artifact Availability:**
- **Public (in this repository):** Evaluation datasets, scalar test vectors, Python analysis and statistical verification pipelines, Vivado constraints, floorplanning scripts, and RFC 8032 functional models.
- **Available on request:** Synthesizable RTL source files, top-level simulation testbenches, and raw oscilloscope binary trace archives (>15 GB) are available from the authors upon request.

