# snr_leakage_calc.py
# Class-conditional leakage SNR and 95% confidence intervals from Welch t:
#   SNR_class = t^2 / (n / 2) = t^2 / 50,000 for n = 100,000 traces/group.

import numpy as np
from tvla_welch_ttest import exact_noncentral_t_ci


def snr_from_t(t, n=100_000):
    snr = (np.asarray(t, dtype=np.float64) ** 2) / (n / 2.0)
    return snr, 10.0 * np.log10(snr)


def main():
    n = 100_000  # 100k traces per group (200k total)

    # QCMW quad-core
    t_qcmw = 4.39
    t_qcmw_ci, snr_db_qcmw_ci = exact_noncentral_t_ci(t_qcmw, n0=n)
    snr_lin_qcmw, snr_db_qcmw = snr_from_t(t_qcmw, n)

    # Single-core baseline
    t_sc = 11.16
    t_sc_ci, snr_db_sc_ci = exact_noncentral_t_ci(t_sc, n0=n)
    snr_lin_sc, snr_db_sc = snr_from_t(t_sc, n)

    delta_snr = float(snr_db_sc - snr_db_qcmw)

    print(
        f"QCMW: peak |t| = {t_qcmw:.2f} (95% CI [{t_qcmw_ci[0]:.2f}, {t_qcmw_ci[1]:.2f}]) "
        f"-> SNR = {snr_lin_qcmw:.2e} ({snr_db_qcmw:.2f} dB, 95% CI [{snr_db_qcmw_ci[0]:.2f}, {snr_db_qcmw_ci[1]:.2f}] dB)"
    )
    print(
        f"Single-core: peak |t| = {t_sc:.2f} (95% CI [{t_sc_ci[0]:.2f}, {t_sc_ci[1]:.2f}]) "
        f"-> SNR = {snr_lin_sc:.2e} ({snr_db_sc:.2f} dB, 95% CI [{snr_db_sc_ci[0]:.2f}, {snr_db_sc_ci[1]:.2f}] dB)"
    )
    print(f"Empirical attenuation: {delta_snr:.2f} dB (4-core 1/N model: 6.02 dB, residual: {delta_snr - 6.02:.2f} dB)")


if __name__ == "__main__":
    main()
