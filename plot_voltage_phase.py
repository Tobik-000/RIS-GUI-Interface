import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def load_data(file_path):
    data = np.load(file_path)
    return data


data = load_data("Utilities/coefficients.npz")

print(data.files)  # List all arrays in the .npz file

frequencies = data["frequencies"]
coefficients = data["coefficients"]
voltages = data["voltages"]
idx = 0  # Index for 5 GHz

max_voltage = voltages.max()


phase_points = np.linspace(0, 360, 1000)


# polynomial evaluation
def volt_map(phase, coeffs):
    num = len(coeffs)
    ret = 0
    for i in range(num):
        ret = ret + coeffs[i] * phase ** (num - 1 - i)
    return ret


voltages_from_phase = np.vectorize(lambda p: volt_map(p, coefficients[idx]))(
    phase_points
)

voltages_from_phase = np.where(
    voltages_from_phase < max_voltage, voltages_from_phase, np.nan
)

fs = 18

plt.figure(figsize=(12, 6))
plt.plot(voltages_from_phase, phase_points, label="5 GHz")
plt.xlabel("Voltage [V]", fontsize=fs)
plt.ylabel("Phase [°]", fontsize=fs)
plt.title("Tuning diagram at 5 GHz", fontsize=fs, pad=10)
plt.grid(True)
plt.tight_layout()
plt.savefig("tuning_diagram_5GHz.png", dpi=300)
