import sys

# Constants matching Hardware
P = 2**255 - 19
A_mont = 486662
A_ed = P - 1  # -1 mod P = A_ed for Curve25519
I = pow(2, (P - 1) // 4, P)

# --- Hardware Primitives (Simulated) ---
def hw_add(a, b): return (a + b) % P
def hw_sub(a, b): return (a - b) % P
def hw_mul(a, b): return (a * b) % P
def hw_sqr(a):    return (a * a) % P

# --- 1. Montgomery Ladder (The FPGA Core) ---
# Input: u (Montgomery X-coordinate), k (scalar)
# Output: (X2, Z2) -> P_k, (X3, Z3) -> P_{k+1}
def montgomery_ladder(u, k_clamped):
    X2, Z2 = 1, 0
    X3, Z3 = u, 1
    
    # Conditional swap (cswap) tracks bit changes across loop iterations
    prev_bit = 0
    
    # Hardware runs 255 iterations (254 down to 0)
    for i in range(254, -1, -1):
        bit = (k_clamped >> i) & 1
        swap = bit ^ prev_bit
        
        if swap:
            X2, X3 = X3, X2
            Z2, Z3 = Z3, Z2
            
        # Differential Addition & Doubling (Common Z)
        # Standard formulas used in the "Monolithic Core"
        A = hw_add(X2, Z2)
        B = hw_sub(X2, Z2)
        C = hw_add(X3, Z3)
        D = hw_sub(X3, Z3)
        
        AA = hw_sqr(A)
        BB = hw_sqr(B)
        DA = hw_mul(D, A)
        CB = hw_mul(C, B)
        
        X3 = hw_sqr(hw_add(DA, CB))
        Z3 = hw_mul(u, hw_sqr(hw_sub(DA, CB)))
        X2 = hw_mul(AA, BB)
        
        E = hw_sub(AA, BB)
        a24 = 121665
        Z2 = hw_mul(E, hw_add(AA, hw_mul(a24, E)))
        
        prev_bit = bit

    # Final Swap if needed
    if prev_bit:
        X2, X3 = X3, X2
        Z2, Z3 = Z3, Z2
        
    return X2, Z2, X3, Z3

# --- 2. Y-Coordinate Recovery (FPGA Quad-Core Schedule) ---
# Input: Ladder State (X2, Z2, X3, Z3), Initial u
# Output: (X_rec, Y_rec, Z_rec) Projective
def y_coordinate_recovery(X2, Z2, X3, Z3, u):
    # Mapping Algorithm 4 (Okeya-Sakurai Hardware Schedule) to 4 Cores
    
    # [Round 1]
    # Core 1: T1 = u * Z2
    T1 = hw_mul(u, Z2)
    # Core 2: TA = 2A * Z2  (2A = 2*486662 = 973324)
    TA = hw_mul(973324, Z2)
    # Core 3: T4_pre = u * X2
    T4_pre = hw_mul(u, X2)
    # Core 4: TB = 2B * 1 (Note: B_mont = 1 for Curve25519) -> 2 * 1 = 2
    TB = 2 
    
    # [ALU Operations]
    T2 = hw_add(X2, T1)
    T3 = hw_sub(X2, T1)
    T2a = hw_add(T2, TA)
    T4 = hw_add(T4_pre, Z2)
    
    # [Round 2]
    # Core 1: T3_sq = T3^2
    T3_sq = hw_sqr(T3)
    # Core 2: T1a = TA * Z2
    T1a = hw_mul(TA, Z2)
    # Core 3: T2b = T2a * T4
    T2b = hw_mul(T2a, T4)
    # Core 4: T_Ba = TB * Z2
    T_Ba = hw_mul(TB, Z2)
    
    # [Round 3]
    # Core 1: T_Num2 = T3_sq * X3
    T_Num2 = hw_mul(T3_sq, X3)
    # Core 2: T1aZ = T1a * Z3
    T1aZ = hw_mul(T1a, Z3)
    # Core 3: T2bZ = T2b * Z3
    T2bZ = hw_mul(T2b, Z3)
    # Core 4: T_Den1 = T_Ba * Z3
    T_Den1 = hw_mul(T_Ba, Z3)
    
    # [ALU Ops]
    # T_NumDiff = T2bZ - T1aZ
    T_NumDiff = hw_sub(T2bZ, T1aZ)
    # Y_mid = T_NumDiff - T_Num2
    Y_mid = hw_sub(T_NumDiff, T_Num2)
    
    # [Round 4]
    X_rec = hw_mul(T_Den1, X2)
    Z_rec = hw_mul(T_Den1, Z2)
    Y_rec = hw_mul(Y_mid, Z2)
    
    return X_rec, Y_rec, Z_rec

# --- 3. Final Map (CPU Post-Processing) ---
def final_map_cpu(X, Y, Z, u, sign_x_orig):
    # The FPGA returns Projective Montgomery Coordinates (X_rec, Y_rec, Z_rec)
    # where u = X/Z and v = Y/Z.
    
    # 1. Recover u (Montgomery X)
    Z_inv = pow(Z, P - 2, P)
    u_calc = (X * Z_inv) % P
    
    # 2. Map u -> y_ed
    # y = (u - 1) / (u + 1)
    # y = (X/Z - 1) / (X/Z + 1) = (X - Z) / (X + Z)
    
    num = (X - Z) % P
    den = (X + Z) % P
    den_inv = pow(den, P - 2, P)
    y_ed = (num * den_inv) % P
    
    # 3. Recover x_ed from y_ed (Standard Ed25519 Logic)
    # We trust the point is on the curve, so we derive X from Y.
    # x^2 = (y^2 - 1) / (d*y^2 + 1)
    d = -121665 * pow(121666, P - 2, P) % P
    y2 = (y_ed * y_ed) % P
    u_x = (y2 - 1) % P
    v_x = (d * y2 + 1) % P
    v_inv = pow(v_x, P - 2, P)
    x2 = (u_x * v_inv) % P
    
    # Sqrt(x2)
    x_ed = pow(x2, (P + 3) // 8, P)
    if (x_ed * x_ed) % P != x2:
        I = pow(2, (P - 1) // 4, P)
        x_ed = (x_ed * I) % P
        
    # Sign handling (x must be even for standard base point derived keys usually)
    if x_ed % 2 != 0:
        x_ed = P - x_ed
    
    return x_ed, y_ed

# --- Main Test Wrapper ---
def sign_hardware_model(sk_bytes, msg):
    # 1. CPU: Hashing & Clamping
    import hashlib
    h = hashlib.sha512(sk_bytes[:32]).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= (1 << 254)
    
    # Hardware acceleration usually does R = r*G and S = r + k*a
    # This model focuses on the Point Multiplication P = k*G (Verification part)
    # Or R = r*G (Signing part)
    
    # Let's verify standard Point Mul: P = a * G
    # G (Edwards) -> u (Montgomery)
    # G_ed = (x, y) = (1511222134..., 4631683569...)
    # u = (1 + y) / (1 - y)
    Gy = 4 * pow(5, P - 2, P) % P
    u = (1 + Gy) * pow(1 - Gy, P - 2, P) % P
    
    # 2. FPGA: Montgomery Ladder
    X2, Z2, X3, Z3 = montgomery_ladder(u, a)
    
    # 3. FPGA: Y-Recovery
    X_rec, Y_rec, Z_rec = y_coordinate_recovery(X2, Z2, X3, Z3, u)
    
    # 4. CPU: Final Inverse
    x_final, y_final = final_map_cpu(X_rec, Y_rec, Z_rec, u, 0)
    
    # Correct x sign
    if x_final % 2 != 0: # Gx is odd? No, need to check
         pass # Okeya-Sakurai recovers X^2 roughly, sign handling is complex in X-only
         # For pure verification, Y is sufficient to check signature
    
    return x_final, y_final

if __name__ == "__main__":
    print("Design Model Loaded.")
