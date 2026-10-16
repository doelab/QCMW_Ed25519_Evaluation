# QCMW Ed25519 Evaluation Artifacts

This repository provides evaluation artifacts, synthesis constraints, side-channel analysis scripts, and functional verification testbenches for:

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
- QCMW: peak $|t| = 4.39 \implies \text{SNR} = 3.85 \times 10^{-4}$ ($-34.14\text{ dB}$)
- Single-core: peak $|t| = 11.16 \implies \text{SNR} = 2.49 \times 10^{-3}$ ($-26.04\text{ dB}$)
- Empirical attenuation: $8.10\text{ dB}$ ($4\text{-core model}: 6.00\text{ dB}$, stagger gain: $2.10\text{ dB}$).

### 4. TVLA Welch t-Test
Run Welch's two-sample t-test against the standard $|t| < 4.5$ boundary and the trace-wide Mini-p / Sidak threshold over $M = 189{,}790$ samples ($37{,}958\text{ cycles} \times 5\text{ samples/cycle}$):

```bash
cd sca_analysis
python3 tvla_welch_ttest.py
```
*Expected Output:*
- Standard threshold: $|t| < 4.50$ (Standard TVLA: PASS)
- Mini-p / Sidak threshold ($\alpha = 10^{-5}$): $|t_{\text{crit}}| = 6.56$ (Mini-p multiple comparison: PASS)
- Measured peak $|t| = 4.38 \approx 4.39$.

### 5. Calibrated CPA Simulation
Simulate correlation power analysis and trace requirements calibrated to the board noise floor ($\sigma \approx 54.66$, $-34.8\text{ dB}$ model SNR):

```bash
cd sca_analysis
python3 cpa_simulation.py
```
*Expected Output:*
- Per-trace accuracy: $50.73\%$ (theory), matching random guessing within $0.73$ percentage points.
- Peak $|t|$ statistic: $4.39$.
- Minimum Traces to Disclosure (MTD):
  - $\text{MTD}_{90\%} = 4{,}907$ traces
  - $\text{MTD}_{99\%} = 16{,}169$ traces
  - $\text{MTD}_{99.9\%} = 28{,}531$ traces
- Output plots saved in `sca_analysis/cpa_results/`.

---

## Hardware Specifications

Side-channel acquisition runs on a Digilent Nexys A7-100T development board hosting an Artix-7 FPGA (`synthesis_constraints/nexys_a7_100t.xdc`). High-frequency timing closure targets Xilinx Virtex UltraScale+ at 384.62 MHz (`synthesis_constraints/ultrascale_plus_384mhz.xdc`, $T = 2.60\text{ ns}$, WNS = 0.00 ns). Dedicated rectangular Pblocks (`synthesis_constraints/pblock_quadcore_floorplan.xdc`) isolate each of the four CIOS cores into separate DSP columns without spatial overlap.
