# tvla_welch_ttest.py
# Point-wise Welch t-test, Sidak thresholds, noncentral-t 95% CIs, and two-group trace bootstrap.

import argparse
import math
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm, nct


def welch_t(fixed, random):
    """Point-wise Welch two-sample t-statistic between (n0, M) fixed and (n1, M) random traces."""
    n0, n1 = fixed.shape[0], random.shape[0]
    mu0, mu1 = np.mean(fixed, axis=0), np.mean(random, axis=0)
    v0 = np.var(fixed, axis=0, ddof=1)
    v1 = np.var(random, axis=0, ddof=1)
    se = np.sqrt(v0 / n0 + v1 / n1)
    se = np.where(se == 0.0, 1e-12, se)
    return (mu0 - mu1) / se


def sidak_threshold(m, alpha=1e-5):
    """Sidak family-wise critical threshold across M time samples."""
    alpha_point = 1.0 - math.pow(1.0 - alpha, 1.0 / m)
    return float(norm.ppf(1.0 - alpha_point / 2.0))


def exact_noncentral_t_ci(t_obs, n0=100_000, n1=None, alpha=0.05):
    """95% CI at peak sample j* by inverting noncentral-t CDF, propagated to SNR_class (dB)."""
    if n1 is None:
        n1 = n0
    t_abs = abs(float(t_obs))
    df = n0 + n1 - 2
    n_eff = (n0 * n1) / float(n0 + n1)
    half_alpha = alpha / 2.0

    if nct.cdf(t_abs, df, 0.0) < 1.0 - half_alpha:
        theta_low = 0.0
    else:
        theta_low = float(brentq(lambda th: float(nct.cdf(t_abs, df, th)) - (1.0 - half_alpha), 0.0, t_abs + 10.0))

    theta_high = float(brentq(lambda th: float(nct.cdf(t_abs, df, th)) - half_alpha, max(0.0, t_abs - 10.0), t_abs + 10.0))

    snr_low = 10.0 * math.log10((theta_low ** 2) / n_eff) if theta_low > 0.0 else -float("inf")
    snr_high = 10.0 * math.log10((theta_high ** 2) / n_eff)
    return (theta_low, theta_high), (snr_low, snr_high)


def bootstrap_trace_groups(fixed, random, recalc_max=False, n_bootstraps=2000, alpha=0.05, seed=42, batch_size=100):
    """Independent within-group complete-trace bootstrap at peak index j* (or max_j if recalc_max=True)."""
    n0, m0 = fixed.shape
    n1, m1 = random.shape
    if m0 != m1:
        raise ValueError(f"Sample count mismatch: {m0} vs {m1}")

    n_eff = (n0 * n1) / float(n0 + n1)
    j_star = int(np.argmax(np.abs(welch_t(fixed, random))))

    rng = np.random.default_rng(seed)
    boot_t = np.empty(n_bootstraps, dtype=np.float64)

    for start in range(0, n_bootstraps, batch_size):
        end = min(start + batch_size, n_bootstraps)
        cur = end - start
        idx0 = rng.integers(0, n0, size=(cur, n0))
        idx1 = rng.integers(0, n1, size=(cur, n1))
        if not recalc_max:
            f_sub = fixed[idx0, j_star]
            r_sub = random[idx1, j_star]
            m_f = np.mean(f_sub, axis=1)
            m_r = np.mean(r_sub, axis=1)
            v_f = np.var(f_sub, axis=1, ddof=1)
            v_r = np.var(r_sub, axis=1, ddof=1)
            boot_t[start:end] = np.abs(m_f - m_r) / np.sqrt(v_f / n0 + v_r / n1)
        else:
            for b in range(cur):
                t_rep = welch_t(fixed[idx0[b]], random[idx1[b]])
                boot_t[start + b] = float(np.max(np.abs(t_rep)))

    p_low, p_high = 100.0 * (alpha / 2.0), 100.0 * (1.0 - alpha / 2.0)
    t_ci = (float(np.percentile(boot_t, p_low)), float(np.percentile(boot_t, p_high)))
    snr_rep = 10.0 * np.log10((boot_t ** 2) / n_eff)
    snr_ci = (float(np.percentile(snr_rep, p_low)), float(np.percentile(snr_rep, p_high)))
    return t_ci, snr_ci


def make_calibrated_traces(t_obs, n_per_group=100_000, m_window=20, j_star=10, sigma=54.66, seed=100):
    """Synthetic (n_per_group, m_window) trace pair calibrated to |t| = t_obs at j_star."""
    rng = np.random.default_rng(seed)
    fixed = rng.normal(0.0, sigma, size=(n_per_group, m_window))
    random = rng.normal(0.0, sigma, size=(n_per_group, m_window))
    se_peak = np.sqrt(
        np.var(fixed[:, j_star], ddof=1) / n_per_group
        + np.var(random[:, j_star], ddof=1) / n_per_group
    )
    fixed[:, j_star] -= (np.mean(fixed[:, j_star]) - np.mean(random[:, j_star]))
    fixed[:, j_star] += t_obs * se_peak
    return fixed, random


def compute_wilson_score_ci(k, n, confidence=0.95):
    """Wilson score confidence interval for binomial proportion k / n."""
    z = float(norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    p_hat = k / n
    denom = 1.0 + (z ** 2) / n
    center = (p_hat + (z ** 2) / (2.0 * n)) / denom
    margin = (z * math.sqrt(p_hat * (1.0 - p_hat) / n + (z ** 2) / (4.0 * (n ** 2)))) / denom
    return center - margin, center + margin


def main():
    parser = argparse.ArgumentParser(description="TVLA Welch t-test and confidence intervals.")
    parser.add_argument("--fixed", type=str, default=None, help="Optional .npy file of fixed-group traces (n0, M)")
    parser.add_argument("--random", type=str, default=None, help="Optional .npy file of random-group traces (n1, M)")
    parser.add_argument("--bootstraps", type=int, default=2000, help="Bootstrap replicates (default: 2000)")
    args = parser.parse_args()

    if args.fixed and args.random:
        fixed = np.load(args.fixed)
        random = np.load(args.random)
        n0, m_samples = fixed.shape
        n1 = random.shape[0]
        n_eff = (n0 * n1) / float(n0 + n1)
        t_vec = welch_t(fixed, random)
        j_star = int(np.argmax(np.abs(t_vec)))
        peak_t = float(abs(t_vec[j_star]))
        snr_db = 10.0 * math.log10((peak_t ** 2) / n_eff)
        t_ci, snr_ci = exact_noncentral_t_ci(peak_t, n0=n0, n1=n1)
        boot_t, boot_snr = bootstrap_trace_groups(fixed, random, n_bootstraps=args.bootstraps)
        print(f"Loaded traces: fixed={fixed.shape}, random={random.shape}, j*={j_star}")
        print(f"Peak |t| = {peak_t:.2f} (SNR = {snr_db:.2f} dB)")
        print(f"Noncentral-t 95% CI: [{t_ci[0]:.2f}, {t_ci[1]:.2f}] -> SNR [{snr_ci[0]:.2f}, {snr_ci[1]:.2f}] dB")
        print(f"Bootstrap 95% CI:    [{boot_t[0]:.2f}, {boot_t[1]:.2f}] -> SNR [{boot_snr[0]:.2f}, {boot_snr[1]:.2f}] dB")
        return

    m_samples = 189_790  # 37,958 cycles * 5 samples/cycle
    n_per_group = 100_000
    t_crit_1e5 = sidak_threshold(m_samples, alpha=1e-5)
    t_crit_05 = sidak_threshold(m_samples, alpha=0.05)

    print(f"Trace length: {m_samples:,} samples (37,958 cycles x 5 samples/cycle)")
    print("Reference threshold: |t| = 4.50")
    print(f"Sidak threshold (alpha=1e-5): |t_crit| = {t_crit_1e5:.2f}")
    print(f"Sidak threshold (alpha=0.05): |t_crit| = {t_crit_05:.2f}")

    # QCMW quad-core (peak |t| = 4.39, N = 100,000/group)
    t_qcmw = 4.39
    snr_qcmw = 10.0 * math.log10((t_qcmw ** 2) / (n_per_group / 2.0))
    t_ci_q, snr_ci_q = exact_noncentral_t_ci(t_qcmw, n0=n_per_group)
    fix_q, rnd_q = make_calibrated_traces(t_qcmw, n_per_group=n_per_group, seed=100)
    boot_t_q, boot_snr_q = bootstrap_trace_groups(fix_q, rnd_q, n_bootstraps=args.bootstraps, seed=42)

    print(f"\nQCMW (N = {n_per_group:,}/group):")
    print(f"  Peak |t| at j*          = {t_qcmw:.2f} (SNR = {snr_qcmw:.2f} dB)")
    print(f"  Noncentral-t 95% CI     = [{t_ci_q[0]:.2f}, {t_ci_q[1]:.2f}] -> SNR [{snr_ci_q[0]:.2f}, {snr_ci_q[1]:.2f}] dB")
    print(f"  Trace bootstrap (B={args.bootstraps}) = [{boot_t_q[0]:.2f}, {boot_t_q[1]:.2f}] -> SNR [{boot_snr_q[0]:.2f}, {boot_snr_q[1]:.2f}] dB")

    # Single-core baseline (peak |t| = 11.16, N = 100,000/group)
    t_sc = 11.16
    snr_sc = 10.0 * math.log10((t_sc ** 2) / (n_per_group / 2.0))
    t_ci_sc, snr_ci_sc = exact_noncentral_t_ci(t_sc, n0=n_per_group)
    fix_sc, rnd_sc = make_calibrated_traces(t_sc, n_per_group=n_per_group, seed=101)
    boot_t_sc, boot_snr_sc = bootstrap_trace_groups(fix_sc, rnd_sc, n_bootstraps=args.bootstraps, seed=42)

    print(f"\nSingle-core baseline (N = {n_per_group:,}/group):")
    print(f"  Peak |t| at j*          = {t_sc:.2f} (SNR = {snr_sc:.2f} dB)")
    print(f"  Noncentral-t 95% CI     = [{t_ci_sc[0]:.2f}, {t_ci_sc[1]:.2f}] -> SNR [{snr_ci_sc[0]:.2f}, {snr_ci_sc[1]:.2f}] dB")
    print(f"  Trace bootstrap (B={args.bootstraps}) = [{boot_t_sc[0]:.2f}, {boot_t_sc[1]:.2f}] -> SNR [{boot_snr_sc[0]:.2f}, {boot_snr_sc[1]:.2f}] dB")

    # Wilson score 95% CI for single-trace classification (50,729 / 100,000)
    w_low, w_high = compute_wilson_score_ci(50_729, 100_000)
    print(f"\nSingle-trace classification Wilson 95% CI (50.73%, N=100k): [{w_low*100:.2f}%, {w_high*100:.2f}%]")


if __name__ == "__main__":
    main()
