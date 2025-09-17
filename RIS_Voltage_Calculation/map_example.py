import numpy as np
import matplotlib.pyplot as plt

# polynomial mapping from phase (degrees) to voltage (V)
def volt_map(phase, coeffs):
    num = len(coeffs)
    ret = 0
    for i in range(num):
        ret = ret + coeffs[i]*phase**(num-1-i)
    return ret


phase_file = "phases.npz"
coeff_file = "coefficients.npz"

phase_data = np.load(phase_file)
print(phase_data)
frequencies = phase_data["frequencies"]
voltages = phase_data["voltages"]
phases = phase_data["phases"]

coeff_data = np.load(coeff_file)
print(coeff_data)
coeffs = coeff_data["coefficients"]

print("Frequency shape:", frequencies.shape)
print("Voltage shape:", voltages.shape)
print("Phase shape:", phases.shape)
print("Coefficient shape:", coeffs.shape)

freq1_idx = 0 # 5GHz
freq2_idx = 600 # 5.6GHz

p2 = np.linspace(0,330) # Example phase angle range. Typically lower than 330°
plt.figure(dpi=150)


fit_voltages = volt_map(p2, coeffs[freq1_idx]) # Generate voltages for phases using the previously generated coefficients
plt.scatter(voltages, phases[freq1_idx], label=f'{frequencies[freq1_idx]/1e9:.2f} GHz Source')
plt.plot(fit_voltages, p2, label=f'{frequencies[freq1_idx]/1e9:.2f} GHz fitted polynomial', color='green')


fit_voltages = volt_map(p2, coeffs[freq2_idx]) # Generate voltages for phases using the previously generated coefficients
plt.scatter(voltages, phases[freq2_idx], label=f'{frequencies[freq2_idx]/1e9:.2f} GHz Source')
plt.plot(fit_voltages, p2, label=f'{frequencies[freq2_idx]/1e9:.2f} GHz fitted polynomial', color='green', linestyle="--")

plt.xlabel("RIS Setting Voltage in V")
plt.ylabel("Phase in deg")
plt.grid()
plt.legend()
plt.savefig("RIS_phase_voltage_map.png")


# new code:
print("#"*60)

# calculate required phase for specific angle
desired_angle = 50 # degrees
wavelength = 3e8 / (frequencies[freq1_idx]) # wavelength
element_spacing =  2*0.015 # element spacing

required_phase = (360 * element_spacing * np.sin(np.radians(desired_angle)) / wavelength) % 360
print(f"Required phase for {desired_angle}° beam at {frequencies[freq1_idx]/1e9:.2f} GHz: {required_phase:.2f}°")

# get Voltage for specific phase at 5.0GHz
voltage_1_5GHz = volt_map(required_phase, coeffs[freq1_idx])
voltage_2_5GHz = volt_map(2*required_phase, coeffs[freq1_idx])
print(f"Voltage for {required_phase:.2f}° phase at {frequencies[freq1_idx]/1e9:.2f} GHz: {voltage_1_5GHz:.3f} V")
print(f"Voltage for {2*required_phase:.2f}° phase at {frequencies[freq1_idx]/1e9:.2f} GHz: {voltage_2_5GHz:.3f} V")