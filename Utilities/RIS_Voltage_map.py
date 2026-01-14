import numpy as np
import os


def _rotate_into_window(angles_deg, window_width=290.0, atol=1e-9):
    """
    Given angles in [0,360), find a global rotation c such that
    (angles + c) mod 360 lies inside [0, window_width] if possible.

    Returns rotated angles (in [0, window_width]) and the rotation c (deg).
    Raises ValueError if impossible.
    """
    a = np.sort(np.mod(angles_deg, 360.0))
    N = len(a)
    # Largest gap approach: the minimal arc covering all points is 360 - max_gap
    diffs = np.diff(np.concatenate([a, [a[0] + 360.0]]))
    k = int(np.argmax(diffs))
    max_gap = diffs[k]
    span = 360.0 - max_gap  # width of minimal circular arc containing all points

    if span <= window_width + atol:
        # Start of the minimal arc is the element right after the largest gap
        start = a[(k + 1) % N]
        c = -start
        rotated = (angles_deg + c) % 360.0
        # Numerical safety: clip tiny overshoots
        rotated = np.clip(rotated, 0.0, window_width)
        return rotated, c, span
    else:
        raise ValueError(
            f"Cannot fit all phases into [0, {window_width}] without changing the beam. "
            f"Minimal required span is {span:.2f}° > {window_width}°. "
            f"Consider reducing spacing, scan angle, or frequency."
        )


def steering_phases(theta_deg, phi_deg, dy=None, dz=None, max_phase=290.0):
    """
    Compute the 3x3 phase shifts (in degrees) for beam steering and map them
    so that every command lies within [0, max_phase] while preserving functionality.

    Parameters
    ----------
    theta_deg : float
        Elevation angle in degrees, range [-90, 90].
    phi_deg : float
        Azimuth angle in degrees, range [-180, 180].
    dx : float
        Element spacing in x-direction (meters). Default: 0.03 m.
    dy : float
        Element spacing in y-direction (meters). Default: 0.03 m.
    max_phase : float
        Allowed command range upper bound (degrees). Default: 250.

    Returns
    -------
    phases : 2D numpy.ndarray (3x3)
        Phase shift for each element in degrees, constrained to [0, max_phase].
    info : dict
        Diagnostics: {'rotation_deg': c, 'span_deg': span_before_mapping}
    """
    if dy is None:
        dy = 0.03
    if dz is None:
        dz = 0.03

    frequency = 5e9  # 5 GHz
    wavelength = 3e8 / frequency

    k = 2 * np.pi / wavelength
    theta = np.deg2rad(theta_deg)
    phi = np.deg2rad(phi_deg)

    # Progressive phase steps
    dphi_y = -k * dy * np.cos(theta) * np.sin(phi)
    dphi_z = -k * dz * np.sin(theta)

    # Build base phases in degrees, wrapped to [0,360)
    base = []
    idx_map = []  # (j,i) to put them back into 3x3
    real_idx = []
    for i, m in enumerate([-1, 0, 1]):  # y-direction index (columns)
        for j, n in enumerate([-1, 0, 1]):  # z-direction index (rows)
            phase = m * dphi_y + n * dphi_z
            phase_deg = np.rad2deg(phase) % 360.0
            base.append(phase_deg)
            idx_map.append((j, i))
            real_idx.append((n, m))

    base = np.array(base)

    # Find rotation that fits all into [0, max_phase]
    phase_values_in_window, c_deg, span = _rotate_into_window(base, window_width=max_phase)

    # Restore 3x3 array in the original (row=j, col=i) layout
    phases_in_window = np.zeros((3, 3))
    phases = np.zeros((3, 3))
    
    for phase_value_in_window, (j, i), phase_value in zip(phase_values_in_window, idx_map, base):
        phases_in_window[j, i] = phase_value_in_window
        phases[j, i] = phase_value
        
    print("-"*60)
    print(f"Steering angles: theta={theta_deg}°, phi={phi_deg}°: ")
    # Print phase mapping info
    print("Phase mapping info:")
    print(f"  Original phases (deg):\n{phases}")
    print(f"  Mapped phases (deg):\n{phases_in_window}")
    print(f"  Index map (row, col): {idx_map}")
    print(f"  Real index (n, m): {real_idx}")
    
    
    info = {"rotation_deg": c_deg, "span_deg": span}
    return phases_in_window, info

import numpy as np

def _invert_volt_map_lut(voltages, coeffs_1d, max_phase=290.0, lut_points=20001):
    """
    Invert volt_map(phase) ~= voltage using a lookup table + interpolation.
    Assumes the mapping is (mostly) monotonic over [0, max_phase].
    """
    phase_grid = np.linspace(0.0, max_phase, lut_points)
    v_grid = volt_map(phase_grid, coeffs_1d)

    # Sort by voltage to make np.interp work even if mapping is decreasing.
    order = np.argsort(v_grid)
    v_sorted = v_grid[order]
    p_sorted = phase_grid[order]

    v = np.asarray(voltages, dtype=float)
    # Clip to LUT voltage range to avoid extrapolation surprises
    v_clipped = np.clip(v, v_sorted[0], v_sorted[-1])
    phases = np.interp(v_clipped, v_sorted, p_sorted)
    return phases


def angle_from_voltage_vector(
    voltage_vector,
    coeff_path="Utilities/coefficients.npz",
    freq_idx=0,
    dy=0.03,
    dz=0.03,
    max_phase=290.0,
    lut_points=20001,
    return_phi_alternatives=False,
):
    """
    Estimate (theta, phi) from a 3x3 RIS voltage configuration.

    - voltage_vector: flattened length-9 vector, same ordering you used in ris_voltage_vector().
    - Returns angles in degrees.
    """
    voltage_vector = np.asarray(voltage_vector, dtype=float)
    if voltage_vector.size != 9:
        raise ValueError("voltage_vector must have length 9.")

    # 1) Voltages -> phases in [0, max_phase]
    coeff_data = np.load(coeff_path)
    coeffs = coeff_data["coefficients"]
    phases_win = _invert_volt_map_lut(voltage_vector, coeffs[freq_idx], max_phase=max_phase, lut_points=lut_points)
    phases_win = phases_win.reshape((3, 3))

    # 2) Spatial unwrap (critical because your window-rotation can place the cut inside the array)
    pr = np.deg2rad(phases_win)
    pr = np.unwrap(pr, axis=1, discont=np.pi)  # unwrap across columns (m direction)
    pr = np.unwrap(pr, axis=0, discont=np.pi)  # unwrap across rows (n direction)

    # 3) Fit plane: phase(m,n) ≈ a*m + b*n + c, where a=dphi_y, b=dphi_z (radians)
    m = np.array([-1.0, 0.0, 1.0])  # columns
    n = np.array([-1.0, 0.0, 1.0])  # rows
    M, N = np.meshgrid(m, n)        # M: col coordinate, N: row coordinate

    A = np.column_stack([M.ravel(), N.ravel(), np.ones(9)])
    y = pr.ravel()
    a, b, _c = np.linalg.lstsq(A, y, rcond=None)[0]  # a=dphi_y, b=dphi_z

    dphi_y = a
    dphi_z = b

    # 4) Invert the steering equations (match your steering_phases() signs) :contentReference[oaicite:2]{index=2}
    frequency = 5e9
    wavelength = 3e8 / frequency
    k = 2 * np.pi / wavelength

    # theta from dphi_z = -k*dz*sin(theta)
    s_theta = -dphi_z / (k * dz)
    s_theta = np.clip(s_theta, -1.0, 1.0)
    theta_rad = np.arcsin(s_theta)

    # phi from dphi_y = -k*dy*cos(theta)*sin(phi)
    c_theta = np.cos(theta_rad)
    if np.isclose(c_theta, 0.0, atol=1e-9):
        # At +/-90° elevation, phi is not observable from your model (cos(theta)=0).
        phi_rad = 0.0
    else:
        s_phi = -dphi_y / (k * dy * c_theta)
        s_phi = np.clip(s_phi, -1.0, 1.0)
        phi_rad = np.arcsin(s_phi)  # principal solution in [-pi/2, pi/2]

    theta_deg = np.rad2deg(theta_rad)  # already in [-90,90]
    phi_deg = np.rad2deg(phi_rad)      # principal in [-90,90]

    # Optional: second azimuth solution due to sin ambiguity (phi and 180-phi have same sin)
    if return_phi_alternatives:
        phi2_deg = 180.0 - phi_deg
        # normalize both to [-180,180)
        phi_deg_n = (phi_deg + 180.0) % 360.0 - 180.0
        phi2_deg_n = (phi2_deg + 180.0) % 360.0 - 180.0
        return theta_deg, (phi_deg_n, phi2_deg_n)

    # normalize to [-180,180)
    phi_deg = (phi_deg + 180.0) % 360.0 - 180.0
    
    
    print(f"Recovered angles: theta= {theta_deg:.2f}°, phi= {phi_deg:.2f}°")
    
    return theta_deg, phi_deg





# Function to compute voltage vector for given theta and phi


def ris_voltage_vector(
    theta_deg,
    phi_deg,
    coeff_path="Utilities/coefficients.npz",
    freq_idx=0,
    max_phase=290.0,
):
    """
    Compute the voltage vector for the RIS for given steering angles.

    Parameters
    ----------
    theta_deg : float
        Elevation angle in degrees.
    phi_deg : float
        Azimuth angle in degrees.
    coeff_path : str
        Path to the coefficients .npz file.
    freq_idx : int
        Frequency index to use from coefficients.
    max_phase : float
        Maximum allowed phase (degrees).

    Returns
    -------
    voltage_vector : list
        Flattened voltage vector (length 9, reversed order).
    phases : 2D numpy.ndarray
        3x3 phase matrix (degrees).
    voltages : 2D numpy.ndarray
        3x3 voltage matrix (V).
    info : dict
        Diagnostics from phase calculation.
    """
    # Load coefficients
    coeff_data = np.load(coeff_path)
    coeffs = coeff_data["coefficients"]



    # Calculate phases and voltages
    phases, info = steering_phases(theta_deg, phi_deg, max_phase=max_phase)
    voltages = np.vectorize(lambda p: volt_map(p, coeffs[freq_idx]))(phases)
    voltage_vector = voltages.round(2).flatten().tolist()
    return voltage_vector, phases, voltages, info

def volt_map(phase, coeffs):
    num = len(coeffs)
    ret = 0
    for i in range(num):
        ret = ret + coeffs[i] * phase ** (num - 1 - i)
    return ret


def load_data_from_directory(folder_path):
    # Build a sorted list of (label, vector) pairs and a label->vector mapping
    entries = []
    for file in os.listdir(folder_path):
        if file.endswith(".npz"):
            data = np.load(os.path.join(folder_path, file))
            if (
                "ris_settings" in data
                and "target_azimuth" in data
                and "target_elevation" in data
            ):
                az = data["target_azimuth"].item()
                el = data["target_elevation"].item()
                label = f"theta={el}, phi={az}"
                vector = data["ris_settings"].round(2)
                entries.append((el, az, label, vector))
    # Sort by elevation, then azimuth
    entries.sort()
    labels = [label for _, _, label, _ in entries]
    label_to_data = {
        label: {"vector": vector.tolist(), "azimuth": az, "elevation": el}
        for el, az, label, vector in entries
    }
    return labels, label_to_data
