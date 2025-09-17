#!/usr/bin/env python3
"""
Dual-Mode Input GUI (Angles or String)

This program presents a simple graphical user interface with two input modes:
(1) Angle mode: accepts two angular quantities—theta (θ) and phi (φ)—with domain
    constraints θ ∈ [−90°, 90°] and φ ∈ [−180°, 180°].
(2) String mode: accepts an arbitrary UTF-8 text string.

Submitted inputs are validated (angles) and then displayed in a read-only
results panel for transparent, reproducible handling of user data.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from RIS_Voltage_Calculation.RIS_Voltage_map import ris_voltage_vector
from connecting_to_pi import initialize_COM_port, send_to_pi, config_RIS
import threading
import time


class DualInputApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Threading for listening to serial responses
        self.listening = False
        self.listener_thread = None

        # --- Window configuration ---
        self.title("Dual-Mode Input: Angles (θ, φ) or String")
        self.geometry("640x640")
        self.minsize(560, 380)

        # --- Top-level layout frames ---
        self._build_header()
        self._build_tabs()
        self._build_output()

        # Initialize COM port and configure RIS
        if initialize_COM_port():
            config_RIS(0, "0-10V")
            self._write_output("COM port initialized successfully.\n", {})
            self.start_listener()
        else:
            self._write_output("Failed to initialize COM port.\n", {})

        # Keyboard shortcuts
        self.bind("<Control-Return>", lambda e: self._on_submit())
        self.bind("<Escape>", lambda e: self.quit())

    def listen_for_responses(self):
        from connecting_to_pi import ser

        self.listening = True
        while self.listening:
            try:
                if ser and ser.in_waiting > 0:
                    response = ser.readline().decode("utf-8").strip()
                    if response:
                        self._write_output(f"Received from Pi:", {"response": response})
            except Exception as e:
                self._write_output(f"Error reading from serial: {e}", {})
                break
            time.sleep(0.01)

    def start_listener(self):
        if not self.listening:
            self.listener_thread = threading.Thread(
                target=self.listen_for_responses, daemon=True
            )
            self.listener_thread.start()

    def stop_listener(self):
        self.listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1)
            self.listener_thread = None

    # ---------------- UI Construction ----------------
    def _build_header(self):
        header = ttk.Frame(self, padding=(12, 10))
        header.pack(fill="x")

        title_lbl = ttk.Label(
            header, text="RIS Control Interface", font=("Segoe UI", 14, "bold")
        )
        title_lbl.pack(anchor="w")

        expl = (
            "Choose a mode below. In “Angles (θ, φ)” you may provide two angles with the "
            "following admissible ranges: θ ∈ [−90°, 90°], φ ∈ [−180°, 180°].\n"
            "Alternatively, switch to “String Input” to enter an arbitrary voltage vector."
        )
        expl_lbl = ttk.Label(header, text=expl, wraplength=600, justify="left")
        expl_lbl.pack(anchor="w", pady=(6, 0))

    def _build_tabs(self):
        self.nb = ttk.Notebook(self, height=120)
        self.nb.pack(fill="x", expand=False, padx=12, pady=(4, 6))

        # ---- Tab 1: Angles ----
        self.angles_tab = ttk.Frame(self.nb, padding=12)
        self.angles_tab.pack_propagate(False)
        self.nb.add(self.angles_tab, text="Angles (θ, φ)")

        grid = ttk.Frame(self.angles_tab)
        grid.pack(anchor="w", pady=(0, 6))

        # theta
        ttk.Label(grid, text="θ (deg):").grid(row=0, column=0, sticky="w", pady=4)
        self.theta_var = tk.StringVar()
        ttk.Label(grid, text="∈ [−90°, 90°]").grid(row=0, column=2, sticky="w", pady=4)
        self.theta_var = tk.StringVar()
        theta_entry = ttk.Entry(grid, textvariable=self.theta_var, width=12)
        theta_entry.grid(row=0, column=1, sticky="w", padx=(6, 18))
        theta_entry.insert(0, "0")

        # phi
        ttk.Label(grid, text="φ (deg):").grid(row=1, column=0, sticky="w", pady=4)
        self.phi_var = tk.StringVar()
        ttk.Label(grid, text="∈ [−180°, 180°]").grid(
            row=1, column=2, sticky="w", pady=4
        )
        self.phi_var = tk.StringVar()
        phi_entry = ttk.Entry(grid, textvariable=self.phi_var, width=12)
        phi_entry.grid(row=1, column=1, sticky="w", padx=(6, 18))
        phi_entry.insert(0, "0")

        # Angle help text
        help_text = (
            "Scientific note: θ typically denotes elevation in [−90°, 90°], "
            "while φ denotes azimuth in [−180°, 180°]. Values outside these "
            "domains are considered invalid and will be rejected."
        )
        ttk.Label(self.angles_tab, text=help_text, wraplength=580, justify="left").pack(
            anchor="w"
        )

        # ---- Tab 2: String Input ----
        self.string_tab = ttk.Frame(self.nb, padding=12, height=140)
        self.string_tab.pack_propagate(False)
        self.nb.add(self.string_tab, text="String Input")

        ttk.Label(self.string_tab, text="Enter vector:").pack(anchor="w")
        self.string_var = tk.StringVar()
        self.string_entry = ttk.Entry(
            self.string_tab, textvariable=self.string_var, width=60
        )
        self.string_entry.pack(anchor="w", pady=(4, 6), fill="x")

        string_expl = (
            "Enter a UTF-8 string representing a voltage vector of length 9, e.g., "
            "[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]"
        )
        ttk.Label(
            self.string_tab, text=str(string_expl), wraplength=580, justify="left"
        ).pack(anchor="w")

        # Preprogrammed strings
        preprogrammed = [
            "[7.8, 5.0, 0.0, 7.8, 5.0, 0.0, 7.8, 5.0, 0.0]",  # phi= 50, theta= 00
            "[0.0, 5.0, 7.8, 0.0, 5.0, 7.8, 0.0, 5.0, 7.8]",  # phi=-50, theta= 00
            "[7.9, 6.0, 4.7, 5.7, 4.6, 1.1, 4.3, 0.1, 8.0]",  # phi= 50, theta=-45
            "[8.0, 0.1, 4.3, 1.1, 4.6, 5.7, 4.7, 6.0, 7.9]",  # phi= 50, theta= 45
        ]
        self.combobox = ttk.Combobox(
            self.string_tab, values=preprogrammed, state="readonly", width=40
        )
        self.combobox.pack(anchor="w", pady=(0, 4))
        self.combobox.bind(
            "<<ComboboxSelected>>",
            lambda e: self.string_var.set(self.combobox.get()),
        )

        # ---- Submit + Clear controls (shared) ----
        ctrl = ttk.Frame(self, padding=(12, 0))
        ctrl.pack(fill="x", pady=(0, 4))
        ttk.Button(ctrl, text="Submit (Ctrl+Enter)", command=self._on_submit).pack(
            side="left"
        )
        ttk.Button(ctrl, text="Clear", command=self._on_clear).pack(
            side="left", padx=(8, 0)
        )

    def _build_output(self):
        box = ttk.LabelFrame(self, text="Output", padding=10)
        box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.output = tk.Text(box, height=8, wrap="word")
        self.output.pack(fill="both", expand=True)
        self.output.configure(state="disabled")

    # ---------------- Logic ----------------
    def _on_submit(self):
        active = self.nb.index(self.nb.select())

        if active == 0:  # Angles tab
            try:
                theta = float(self.theta_var.get().strip())
                phi = float(self.phi_var.get().strip())
            except ValueError:
                messagebox.showerror("Invalid input", "θ and φ must be numeric.")
                return

            if not (-90.0 <= theta <= 90.0):
                messagebox.showerror("Out of range", "θ must lie within [−90°, 90°].")
                return
            if not (-180.0 <= phi <= 180.0):
                messagebox.showerror("Out of range", "φ must lie within [−180°, 180°].")
                return

            # Construct a normalized result payload
            payload = {
                "mode": "angles",
                "theta_deg": round(theta, 6),
                "phi_deg": round(phi, 6),
            }
            self._write_output("Received valid angles.\n", payload)

            # Calculate corresponding voltage vector
            voltage_vector = ris_voltage_vector(theta, phi)[0]
            self._write_output(
                f"Calculated and sending voltage vector for (theta={theta}, phi={phi}):\n",
                {"voltage_vector": f"{voltage_vector}"},
            )

            send_to_pi(str(voltage_vector) + "\n")

        else:  # String tab
            text = self.string_var.get()
            if text is None or text.strip() == "":
                messagebox.showwarning(
                    "Empty input", "Please enter a non-empty string."
                )
                return

            self._write_output(
                f"Sending Voltage vector:\n",
                {"voltage_vector": text},
            )
            send_to_pi(text + "\n")

    def _on_clear(self):
        self.theta_var.set("0")
        self.phi_var.set("0")
        self.string_var.set("")
        self._set_output_text("")

    def _write_output(self, header, payload: dict):
        # Pretty-print to the Text widget, appending instead of replacing
        divider = "-" * 60
        lines = [header]
        for k, v in payload.items():
            lines.append(f"{k}: {v}")
        lines.append(divider + "\n")
        self.output.configure(state="normal")
        self.output.insert("end", "\n".join(lines))  # Append to the end
        self.output.see("end")  # Scroll to the end
        self.output.configure(state="disabled")

    def _set_output_text(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def destroy(self):
        self.stop_listener()
        super().destroy()


if __name__ == "__main__":
    app = DualInputApp()
    app.mainloop()
