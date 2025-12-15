import os
import numpy as np

# --- what you want to store ---
ris_settings = np.array([7.8, 5.0, 0.0, 7.8, 5.0, 0.0, 7.8, 5.0, 0.0], dtype=float)
target_azimuth = 50   # phi
target_elevation = 0  # theta

# --- where to save ---
out_dir = "test_data"          # change as needed
os.makedirs(out_dir, exist_ok=True)

# Use a filename that encodes theta/phi (optional but handy)
out_path = os.path.join(out_dir, f"theta_{target_elevation}_phi_{target_azimuth}.npz")

# Save keys exactly as your loader expects
np.savez(
    out_path,
    ris_settings=ris_settings,
    target_azimuth=np.array(target_azimuth),
    target_elevation=np.array(target_elevation),
)

print(f"Saved: {out_path}")
