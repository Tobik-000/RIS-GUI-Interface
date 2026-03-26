import os
import numpy as np

        # preprogrammed = [
        #     "[7.8, 5.0, 0.0, 7.8, 5.0, 0.0, 7.8, 5.0, 0.0]",  # phi= 50, theta= 00
        #     "[0.0, 5.0, 7.8, 0.0, 5.0, 7.8, 0.0, 5.0, 7.8]",  # phi=-50, theta= 00
        #     "[7.9, 6.0, 4.7, 5.7, 4.6, 1.1, 4.3, 0.1, 8.0]",  # phi= 50, theta=-45
        #     "[8.0, 0.1, 4.3, 1.1, 4.6, 5.7, 4.7, 6.0, 7.9]",  # phi= 50, theta= 45
        # ]


# --- what you want to store ---
ris_settings = np.array([7.55, 0.6, 4.66, 2.62, 4.96, 6.67, 5.42, 7.24, 0.1], dtype=float)
target_azimuth = -50     # phi
target_elevation = 45  # theta

# --- where to save ---
out_dir = "new_matrix"          # change as needed
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
