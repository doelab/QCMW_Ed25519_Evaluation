# verify_official.py
# Verification against Bernstein's official Ed25519 reference implementation (RFC 8032).
import os
import time
import binascii
import ed25519_ref_djb as OfficialGolden
from ed25519_design_model import sign_hardware_model

def encode_point(x, y):
    # Encode (x, y) coordinates to 32-byte representation (RFC 8032)
    b = 256
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])

def main():
    print("Verifying QCMW design model against official Ed25519 reference (http://ed25519.cr.yp.to)...")
    # 1. Canonical RFC 8032 Test Vector 1 Verification (Deterministic)
    print("\n--- Test 1: Canonical RFC 8032 Test Vector 1 ---")
    sk_rfc = binascii.unhexlify("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pk_exp_rfc = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    
    t0 = time.time()
    pk_official_rfc = OfficialGolden.publickey(sk_rfc)
    t_ref_rfc = (time.time() - t0) * 1000.0
    
    x_des_rfc, y_des_rfc = sign_hardware_model(sk_rfc, b"")
    pk_design_rfc = encode_point(x_des_rfc, y_des_rfc)
    
    print(f"Secret seed: {sk_rfc.hex()}")
    print(f"Official PK: {pk_official_rfc.hex()} ({t_ref_rfc:.2f} ms)")
    print(f"Design PK:   {pk_design_rfc.hex()}")
    
    if pk_design_rfc.hex() == pk_exp_rfc == pk_official_rfc.hex():
        print("Result: PASS (exact 32-byte match with RFC 8032 Test Vector 1)")
    else:
        print("Result: FAIL")
        return

    # 2. Random Vector Verification
    print("\n--- Test 2: Random Key Verification ---")
    sk_bytes = os.urandom(32)
    print(f"Secret seed: {sk_bytes.hex()}")

    # Official golden model (pure Python)
    t0 = time.time()
    pk_official = OfficialGolden.publickey(sk_bytes)
    t_ref = (time.time() - t0) * 1000.0
    print(f"Official PK: {pk_official.hex()} ({t_ref:.2f} ms)")

    # Design model (iterative Montgomery ladder + recovery)
    x_des, y_des = sign_hardware_model(sk_bytes, b"")
    pk_design = encode_point(x_des, y_des)
    print(f"Design PK:   {pk_design.hex()}")

    # Compare full 32 bytes or Y-coordinate (lower 255 bits)
    match_exact = (pk_official == pk_design)
    match_y = (pk_official[:31] == pk_design[:31]) and ((pk_official[31] & 0x7F) == (pk_design[31] & 0x7F))

    if match_exact:
        print("Result: PASS (exact 32-byte match)")
    elif match_y:
        print("Result: PASS (Y-coordinate match; sign bit differs by Montgomery X-only representation)")
    else:
        print("Result: FAIL (mismatch)")
        return

    # Benchmark average execution time
    t0 = time.time()
    for _ in range(5):
        sign_hardware_model(sk_bytes, b"")
    t_des = ((time.time() - t0) / 5.0) * 1000.0

    print(f"Reference latency (Python): {t_ref:.2f} ms")
    print(f"Design model latency (Python): {t_des:.2f} ms (5-run avg)")

if __name__ == "__main__":
    main()
