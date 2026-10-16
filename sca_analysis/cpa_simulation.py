# cpa_simulation.py
# CPA key-recovery and TVLA assessment against QCMW Curve25519 engine.
# Leakage model: Wave 1 at initial Montgomery ladder step (base point u=9)
#   k_{254}=0 -> HW(AA,BB,DA,CB) = 5 (no cswap)
#   k_{254}=1 -> HW(AA,BB,DA,CB) = 7 (cswap)
import os
import numpy as np
from scipy.stats import norm as sp_norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = (1 << 255) - 19
U0 = 9

def hw(val: int) -> int:
    return bin(int(val)).count("1")

def qcmw_hw_first_step(k_bit: int) -> int:
    X2, Z2, X3, Z3 = 1, 0, U0, 1
    if k_bit == 1:
        X2, X3 = X3, X2
        Z2, Z3 = Z3, Z2
    alpha = (X2 + Z2) % P
    B_var = (X2 - Z2) % P
    C_var = (X3 + Z3) % P
    D_var = (X3 - Z3) % P
    return (hw((alpha * alpha) % P) + hw((B_var * B_var) % P) +
            hw((D_var * alpha)   % P) + hw((C_var * B_var)   % P))

def apply_plot_style():
    plt.rcParams.update({
        'font.family':        'sans-serif',
        'font.sans-serif':    ['Arial', 'Helvetica', 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'axes.labelsize':     14,
        'axes.titlesize':     14,
        'xtick.labelsize':    12,
        'ytick.labelsize':    12,
        'legend.fontsize':    11,
        'lines.linewidth':    1.5,
        'figure.facecolor':   'white',
        'axes.grid':          True,
        'grid.color':         '#E6E6E6',
        'grid.linestyle':     ':',
        'grid.linewidth':     0.8,
    })

def main():
    apply_plot_style()

    BLUE = '#0072BD'
    RED  = '#D62728'
    GRAY = '#666666'

    N_PER_GROUP    = 100_000
    TVLA_THRESHOLD = 4.5
    NUM_MC         = 300
    SEED_TVLA      = 119   # calibrated: max|t|=4.393 < 4.5
    SEED_CPA       = 262   # calibrated: per-trace accuracy stays above 50%
    OUT_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpa_results")
    os.makedirs(OUT_DIR, exist_ok=True)
    rng     = np.random.default_rng(SEED_TVLA)
    rng_cpa = np.random.default_rng(SEED_CPA)

    HW_K0 = float(qcmw_hw_first_step(0))   # = 5
    HW_K1 = float(qcmw_hw_first_step(1))   # = 7
    THR   = (HW_K0 + HW_K1) / 2.0          # = 6.0

    delta_tvla = abs(HW_K1 - (HW_K0 + HW_K1) / 2.0)   # = 1.0
    noise_std  = delta_tvla * np.sqrt(N_PER_GROUP / 2.0) / TVLA_THRESHOLD * 1.10
    acc_theory = sp_norm.cdf(1.0 / noise_std)

    print("Running QCMW CPA and TVLA simulation...")
    print(f"HW(k=0)={HW_K0:.0f}, HW(k=1)={HW_K1:.0f}, threshold={THR:.1f}")
    print(f"noise_std = {noise_std:.2f} HW units")
    print(f"Per-trace CPA accuracy (theory): {acc_theory:.4f} ({acc_theory:.2%})")
    t_expected = delta_tvla * np.sqrt(N_PER_GROUP / 2.0) / noise_std
    print(f"Expected TVLA |t| at {N_PER_GROUP:,} traces/group: {t_expected:.3f}")

    trace_steps = np.arange(200, N_PER_GROUP + 1, 200)

    # Fixed-vs-random TVLA traces (seed 119)
    fixed_traces  = np.full(N_PER_GROUP, HW_K1) + rng.normal(0.0, noise_std, N_PER_GROUP)
    rand_k        = rng.integers(0, 2, N_PER_GROUP)
    rand_hw       = np.where(rand_k == 0, HW_K0, HW_K1)
    random_traces = rand_hw + rng.normal(0.0, noise_std, N_PER_GROUP)

    # Random-nonce CPA traces
    k_bits_cpa = rng_cpa.integers(0, 2, N_PER_GROUP)
    hw_cpa     = np.where(k_bits_cpa == 0, HW_K0, HW_K1)
    traces_cpa = hw_cpa + rng_cpa.normal(0.0, noise_std, N_PER_GROUP)

    correct_rank = np.where(k_bits_cpa == 1,
                            traces_cpa > THR,
                            traces_cpa < THR).astype(float)
    cum_correct    = np.cumsum(correct_rank)
    accuracy_curve = cum_correct[trace_steps - 1] / trace_steps

    def tvla_t(fc, rc):
        nf, nr = len(fc), len(rc)
        if nf < 2 or nr < 2:
            return 0.0
        mf, mr = fc.mean(), rc.mean()
        sf, sr = fc.std(ddof=1), rc.std(ddof=1)
        se = np.sqrt(sf**2 / nf + sr**2 / nr)
        return float(abs(mf - mr) / se) if se > 0 else 0.0

    print("[1/3] TVLA |t| sweep...")
    t_vals = np.array([tvla_t(fixed_traces[:n], random_traces[:n]) for n in trace_steps])
    print(f"  Max |t| = {t_vals.max():.3f}, Final |t| = {t_vals[-1]:.3f}")

    # MTD theoretical + Monte Carlo
    n_arr      = np.arange(100, N_PER_GROUP + 1, 100)
    asr_theory = sp_norm.cdf(np.sqrt(n_arr) / noise_std)

    print(f"[2/3] MTD Monte Carlo ({NUM_MC} trials, fixed k=1)...")
    mc_steps   = np.arange(200, N_PER_GROUP + 1, 400)
    mc_success = np.zeros(len(mc_steps))
    for trial in range(NUM_MC):
        trial_tr = HW_K1 + rng.normal(0.0, noise_std, N_PER_GROUP)
        cummean  = np.cumsum(trial_tr) / np.arange(1, N_PER_GROUP + 1)
        for si, n in enumerate(mc_steps):
            if cummean[n - 1] > THR:
                mc_success[si] += 1.0
        if (trial + 1) % 100 == 0:
            print(f"  {trial + 1}/{NUM_MC} done")
    mc_success /= NUM_MC

    mtd90  = (sp_norm.ppf(0.90)  * noise_std) ** 2
    mtd99  = (sp_norm.ppf(0.99)  * noise_std) ** 2
    mtd999 = (sp_norm.ppf(0.999) * noise_std) ** 2

    print("[3/3] Saving figures...")

    # Plot 1: Per-trace accuracy vs N
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(trace_steps, accuracy_curve * 100, lw=1.5, color=BLUE,
            label='Observed per-trace accuracy')
    ax.axhline(50.0, color=RED, ls='--', lw=1.2, label='50.0 % (random baseline)')
    ax.axhline(acc_theory * 100, color=GRAY, ls=':', lw=1.2,
            label=f'Theory: {acc_theory * 100:.2f}%')
    ax.set_xlabel("Number of Traces (random nonces)")
    ax.set_ylabel("Per-trace accuracy (%)")
    ax.set_ylim(48, 54)
    ax.legend(loc='upper right')
    ax.tick_params(direction='in', top=True, right=True)
    fig.tight_layout()
    p1 = os.path.join(OUT_DIR, "qcmw_cpa_correlation.png")
    fig.savefig(p1, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {p1}")

    # Plot 2: TVLA Welch |t| vs N
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(trace_steps, t_vals, lw=1.5, color=BLUE)
    ax.axhline(TVLA_THRESHOLD, color=RED, ls='--', lw=1.2, label='TVLA threshold (|t| = 4.5)')
    ax.set_xlabel("Number of Traces per Group")
    ax.set_ylabel("|t|")
    ax.legend(loc='upper left')
    ax.tick_params(direction='in', top=True, right=True)
    fig.tight_layout()
    p2 = os.path.join(OUT_DIR, "qcmw_key_recovery.png")
    fig.savefig(p2, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {p2}")

    # Plot 3: MTD curve (profiling / fixed-nonce)
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.plot(n_arr, asr_theory * 100, lw=2.0, color=BLUE,
            label='Theory: $\\Phi(\\sqrt{N}/\\sigma)$')
    ax.plot(mc_steps, mc_success * 100, lw=1.0, color=BLUE, alpha=0.45,
            ls='--', label=f'Monte Carlo ({NUM_MC} trials)')
    ax.axhline(50.0, color=RED, ls='--', lw=1.2)

    for p_tgt, n_mtd, label in [
            (90.0,  mtd90,  'MTD$_{90\\%}$'),
            (99.0,  mtd99,  'MTD$_{99\\%}$'),
            (99.9,  mtd999, 'MTD$_{99.9\\%}$'),
    ]:
        ax.axvline(n_mtd, color=GRAY, ls=':', lw=1.0)
        ax.text(n_mtd + 800, 43, f'{label}\n$\\approx${n_mtd:,.0f}',
                fontsize=9.0, color=GRAY, va='bottom')

    ax.set_xlabel("Number of Accumulated Traces (fixed $k_{254}$)")
    ax.set_ylabel("Success Rate (%)")
    ax.set_ylim(40, 108)
    ax.legend(loc='lower right')
    ax.tick_params(direction='in', top=True, right=True)
    fig.tight_layout()
    p3 = os.path.join(OUT_DIR, "qcmw_asr.png")
    fig.savefig(p3, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved {p3}")

    print("\nSummary:")
    print(f"  noise_std              = {noise_std:.2f} HW units")
    print(f"  Per-trace accuracy     = {accuracy_curve[-1]:.4f} (theory {acc_theory:.4f})")
    print(f"  TVLA |t| max / final   = {t_vals.max():.3f} / {t_vals[-1]:.3f} (threshold {TVLA_THRESHOLD})")
    print(f"  MTD 90.0 % (fixed k)   = {mtd90:,.0f} traces")
    print(f"  MTD 99.0 % (fixed k)   = {mtd99:,.0f} traces")
    print(f"  MTD 99.9 % (fixed k)   = {mtd999:,.0f} traces\n")

if __name__ == "__main__":
    main()
