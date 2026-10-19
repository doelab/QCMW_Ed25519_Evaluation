# Compute class-conditional leakage SNR and architectural attenuation from Welch t.
#   SNR = t^2 / (N / 2) = t^2 / 50,000 for N = 100,000 traces/group.

import numpy as np

def snr_from_t(t, n=100000):
    snr = (t ** 2) / (n / 2.0)
    return snr, 10.0 * np.log10(snr)

def main():
    n = 100000  # 100k traces per group (200k total)

    # QCMW quad-core
    t_qcmw = 4.39
    snr_lin_qcmw, snr_db_qcmw = snr_from_t(t_qcmw, n)

    # Single-core baseline
    t_sc = 11.16
    snr_lin_sc, snr_db_sc = snr_from_t(t_sc, n)

    delta_snr = snr_db_sc - snr_db_qcmw

    print(f"QCMW: peak |t| = {t_qcmw:.2f} -> SNR = {snr_lin_qcmw:.2e} ({snr_db_qcmw:.2f} dB)")
    print(f"Single-core: peak |t| = {t_sc:.2f} -> SNR = {snr_lin_sc:.2e} ({snr_db_sc:.2f} dB)")
    print(f"Empirical attenuation: {delta_snr:.2f} dB (4-core heuristic: 6.02 dB, residual: {delta_snr - 6.02:.2f} dB)")

if __name__ == "__main__":
    main()
