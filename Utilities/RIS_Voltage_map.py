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


def steering_phases(theta_deg, phi_deg, dx=None, dy=None, max_phase=290.0):
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
    if dx is None:
        dx = 0.03
    if dy is None:
        dy = 0.03

    frequency = 5e9  # 5 GHz
    wavelength = 3e8 / frequency

    k = 2 * np.pi / wavelength
    theta = np.deg2rad(theta_deg)
    phi = np.deg2rad(phi_deg)

    # Progressive phase steps
    dphi_x = -k * dx * np.sin(theta) * np.cos(phi)
    dphi_y = -k * dy * np.sin(theta) * np.sin(phi)

    # Build base phases in degrees, wrapped to [0,360)
    base = []
    idx_map = []  # (j,i) to put them back into 3x3
    for i, m in enumerate([-1, 0, 1]):  # x-direction index (columns)
        for j, n in enumerate([-1, 0, 1]):  # y-direction index (rows)
            phase = m * dphi_x + n * dphi_y
            phase_deg = np.rad2deg(phase) % 360.0
            base.append(phase_deg)
            idx_map.append((j, i))

    base = np.array(base)

    # Find rotation that fits all into [0, max_phase]
    rotated, c_deg, span = _rotate_into_window(base, window_width=max_phase)

    # Restore 3x3 array in the original (row=j, col=i) layout
    phases = np.zeros((3, 3))
    for val, (j, i) in zip(rotated, idx_map):
        phases[j, i] = val

    info = {"rotation_deg": c_deg, "span_deg": span}
    return phases, info


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

    def volt_map(phase, coeffs):
        num = len(coeffs)
        ret = 0
        for i in range(num):
            ret = ret + coeffs[i] * phase ** (num - 1 - i)
        return ret

    # Calculate phases and voltages
    phases, info = steering_phases(theta_deg, phi_deg, max_phase=max_phase)
    voltages = np.vectorize(lambda p: volt_map(p, coeffs[freq_idx]))(phases)
    voltage_vector = voltages.round(2).flatten().tolist()[::-1]
    return voltage_vector, phases, voltages, info


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
