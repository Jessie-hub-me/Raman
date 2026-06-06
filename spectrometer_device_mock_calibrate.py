# -*- coding: utf-8 -*-
"""
@author: zhy86
"""

import os
import re
import time
import glob
import numpy as np


# Place all .asc files in this folder. Replace this with your own path.
DATA_FOLDER = r"F:\Research\Raman_data"

# In the .asc file header, Andor software uses this to generate the center wavelength (nm) for the cm⁻¹ column.
ASC_CENTER_NM = 532.0


def _read_center_from_header(filepath, default_nm=ASC_CENTER_NM):
    """Read the line “Wavelength (nm): 532” from the .asc file header and return the center wavelength (nm).
    If it cannot be found, return default_nm. Note that the header may be at the end of the file, so scan the entire file."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            for line in f:
                m = re.search(r"Wavelength\s*\(nm\)\s*:\s*([\d.]+)", line)
                if m:
                    return float(m.group(1))
    except Exception as e:
        print("Header read warning:", e)
    return default_nm


def _load_asc(filepath):
    """Reads an .asc file and returns (wavelengths_in_meters, intensity).

    The first column of the .asc file contains the Raman shift (cm⁻¹) already calculated by Andor software; it is generated using the
    central wavelength (536 nm) specified in the file header. To restore Andor’s original “absolute wavelength axis,” you must use the same
    536 nm value for calibration. This ensures that the mock wavelength axis matches what the real hardware returns via `get_calibration()`.
    The return units are in meters, consistent with the real hardware’s `self.wavelengths`.
    """
    asc_ref_nm = _read_center_from_header(filepath)

    rows = []
    with open(filepath, "r", errors="ignore") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                if rows:        # The data has already been read; an empty row or a row with a single column indicates the end of the data section.
                    break
                continue        # I haven't started reading the data yet; skip the header at the beginning.
            try:
                x = float(parts[0]); y = float(parts[1])
            except ValueError:
                if rows:        
                    break
                continue        
            rows.append((x, y))

    data = np.array(rows, dtype=float)
    raman_shift = data[:, 0]    
    intensity   = data[:, 1]

    wavelengths_nm = 1.0 / (1.0 / asc_ref_nm - raman_shift / 1e7)
    wavelengths_m  = wavelengths_nm * 1e-9

    return wavelengths_m, intensity


class SpectrometerDevice:
    """Mock device. Same public interface as the real one."""

    def __init__(self, initial_center_nm=532.0, data_folder=DATA_FOLDER):
        print("Initializing MOCK spectrometer (file-based, CALIBRATE)...")
        self.data_folder = data_folder

        # Recursive search for .asc
        # recursive=True + ** It will scan subfolders as well; it also supports files placed directly in the root directory.
        pattern = os.path.join(self.data_folder, "**", "*.asc")
        self.files = sorted(glob.glob(pattern, recursive=True))
        if not self.files:
            self.files = sorted(glob.glob(os.path.join(self.data_folder, "*.asc")))
        if not self.files:
            raise FileNotFoundError(f"No .asc files found in {self.data_folder}")

        print(f"Found {len(self.files)} .asc files in {self.data_folder}")
        for f in self.files:
            print("  -", os.path.basename(f))

        self.current_file_index = 0

        self.wavelengths, self._spectrum = _load_asc(self.files[0])

        # Simulate hardware status
        self.center_wavelength_nm = initial_center_nm
        self._exposure = 0.1            #second
        self._cooler_on = True
        self._temperature = -70.0       # °C

        print(f"Center wavelength: {initial_center_nm} nm (mock)")
        print(f"Wavelength range: {self.wavelengths.min()*1e9:.1f} - "
              f"{self.wavelengths.max()*1e9:.1f} nm")
        print("Mock spectrometer initialization complete")


    def set_center_wavelength(self, wavelength_nm):
        try:
            self.center_wavelength_nm = wavelength_nm
            time.sleep(0.2)
            print(f"[MOCK] Center wavelength set to {wavelength_nm} nm")
            print(f"Wavelength range: {self.wavelengths.min()*1e9:.1f} - "
                  f"{self.wavelengths.max()*1e9:.1f} nm")
            return True
        except Exception as e:
            print("Set center wavelength error:", e)
            return False

    def set_exposure(self, exposure):
        self._exposure = exposure

    def get_spectrum(self):
        """Returns the tone data for the currently selected file, with a small amount of random noise added to simulate exposure."""
        try:
            time.sleep(min(self._exposure, 0.5))
            noise = np.random.normal(0, np.sqrt(np.maximum(self._spectrum, 1)) * 0.05)
            return self._spectrum + noise
        except Exception as e:
            print("Spectrum acquisition error:", e)
            return np.zeros(len(self.wavelengths))

    def get_temperature(self):
        return self._temperature

    def set_cooler(self, state):
        self._cooler_on = state
        if not state:
            self._temperature += 20.0
        print(f"[MOCK] Cooler {'on' if state else 'off'}")

    def close(self):
        print("Closing MOCK spectrometer...")
        print("Camera closed (mock)")
        print("Spectrograph closed (mock)")

    # Mock only the additional methods

    def list_files(self):
        return [os.path.basename(f) for f in self.files]

    def load_file(self, index):
        if 0 <= index < len(self.files):
            self.wavelengths, self._spectrum = _load_asc(self.files[index])
            self.current_file_index = index
            print(f"[MOCK] Loaded file: {os.path.basename(self.files[index])}")
            return True
        return False