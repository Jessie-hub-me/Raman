# Raman Acquisition and Processing Platform

**Author: Jiaqi Zhang**

A Python platform that combines Andor spectrometer control and Raman data processing in one interface. It carries each spectrum through acquisition, wavelength to Raman shift conversion, baseline correction, normalization, peak detection, and Voigt fitting inside a single PyQt5 window.

The platform uses a three layer design. It separates the device layer, the processing layer, and the GUI layer. It provides two interchangeable implementations. The real version connects to the hardware. The mock version loads data from saved .asc files. Both versions share the same processing layer, so the processing functions behave identically on live spectra and on saved files.

---

## File Structure

The platform has six files in two groups. Each group has three layers.

**Real version (connects to hardware):**

| File | Layer | Role |
|------|-------|------|
| `spectrometer_gui.py` | GUI | Main entry point. Interface and state management. |
| `spectrometer_processing.py` | Processing | Stateless functions for baseline, normalization, peak detection, and Voigt fitting. |
| `spectrometer_device.py` | Device | Drives the CCD and the spectrograph through pylablib and the Andor SDK2. |

**Mock version (loads data from .asc files):**

| File | Layer | Role |
|------|-------|------|
| `spectrometer_gui_mock_calibrate.py` | GUI | Same as above, with an extra file selector dropdown. |
| `spectrometer_processing_mock_calibrate.py` | Processing | Same processing logic as the real version. |
| `spectrometer_device_mock_calibrate.py` | Device | Loads spectra from .asc files. Same interface as the real version. |

Both device layers expose the same set of methods. These are set center wavelength, set exposure, get spectrum, read temperature, control cooler, and close. The upper layers are written only against this method set. They cannot tell whether the device underneath is real hardware or a file reader.

---

## Three Layer Architecture

- **Device layer.** This is the only module that touches the hardware. It carries the highest risk. Methods that command the hardware return a clear success or failure flag. For example, `set_center_wavelength` returns True only after the grating move and the recalibration both finish.
- **Processing layer.** This is a set of independent, stateless functions. Each function does one transform. The GUI calls them in sequence. They hold no state and never touch the hardware, so they run identically on a live spectrum and on a saved file.
- **GUI layer.** This is the only layer that holds state. It owns the device handle, the current raw spectrum, and the history list. It ties the device layer and the processing layer together.

---

## Requirements

```
python >= 3.8
numpy
scipy
pyqtgraph
PyQt5
ramanspy        # wraps pybaselines, provides baseline algorithms
pylablib        # real version only, for the Andor SDK2
```

The real version also needs the Andor SDK2 DLLs. Set the path at the top of `spectrometer_device.py`:

```python
pll.par["devices/dlls/andor_sdk2"] = "your/dll/path/"
pll.par["devices/dlls/andor_shamrock"] = "your/dll/path/"
```

The mock version only needs the .asc files in a data folder. Set the path at the top of `spectrometer_device_mock_calibrate.py`:

```python
DATA_FOLDER = r"your/data/folder/path"
```

The mock device scans subfolders such as LHQuartz and RHQuartz for all .asc files.

---

## Running the Platform

**Real version (connects to hardware):**

```bash
python spectrometer_gui.py
```

**Mock version (reads files):**

```bash
python spectrometer_gui_mock_calibrate.py
```

---

## Workflow

1. **Set acquisition parameters.** Enter the Integration Time in ms and the number of Averages.
2. **Select a file (mock only).** Choose the .asc file to load from the Test File dropdown.
3. **Acquire.** Click Get Spectrum. The GUI takes the requested number of frames, averages them, plots the result live, and saves it to the history.
4. **Set the center wavelength (real version).** Enter the Center Wavelength and click Apply. This physically moves the grating, so it runs on a button rather than live. After a center change the current spectrum is cleared, because the old pixel mapping is no longer valid. You then need to acquire again.
5. **Use the processing options.** Each one redraws the plot immediately:
   - **Baseline Correction.** IRSQR baseline correction with defaults lam=30, quantile=0.01, num_knots=50.
   - **Normalize.** Optional MinMax normalization.
   - **Peak Finder.** Marks peaks with scipy find_peaks. Prominence controls the sensitivity. Use about 500 for raw data and about 0.5 for normalized data.
   - **Raman Shift.** Switches between the wavelength axis and the Raman shift axis in inverse centimeters. The Laser value in nm is a software parameter. It sets the zero point of the Raman shift. Enter the calibrated value by hand after startup, for example about 535.88 nm.
   - **Limit X range.** Shows only the Stokes side and rescales the Y axis to the data inside the window.
6. **Voigt fitting.** Click Fit Peaks (Voigt). Each peak found by Peak Finder is fitted with a Voigt profile. The fit returns the center, the FWHM, the area, and the height. The fit curves are drawn on top of the raw spectrum.

---

## Processing Order

The order of the steps follows physical constraints. You cannot reorder them freely.

1. **Baseline correction first.** A sloping background that is not removed shifts both the detected peak positions and the fitted areas.
2. **Normalization is optional and never runs before fitting.** Normalization rescales the intensities to a fixed range. This destroys the absolute height and area that the fit needs to recover.
3. **Peak detection.** Find peaks on the baseline corrected spectrum, normalized if you chose to.
4. **Voigt fitting.** Fit on baseline corrected and non normalized data, on the Raman shift axis. This way the widths carry physical units and the areas stay meaningful. Each peak is fitted in a local window of plus or minus 40 inverse centimeters, so close peaks do not interfere.

The raw spectrum is always kept. The displayed curve is rebuilt from the raw spectrum whenever a control changes. So every step is reversible and can be compared against the raw data.

---

## Closing the Platform (Real Version)

When you close the window, the real version first turns the cooler off. It then waits until the CCD warms up above 0 degrees Celsius before it releases the hardware and exits. During this time the title shows Warming up DO NOT CLOSE. This protects the CCD. Do not force the window closed. The mock version has no such step and closes right away.

---

## Key Notes

- **Laser wavelength and center wavelength are different.** The laser wavelength is a software only parameter, shown as Laser in the GUI. It is used only to compute the Raman shift axis. The center wavelength is a hardware parameter. It moves the grating motor and sets the detection window on the CCD.
- **Mock wavelength rebuild.** The mock device reads the first column of each .asc file, which is the Raman shift in inverse centimeters that the Andor software already computed. It rebuilds the absolute wavelength axis using the reference wavelength in the file header. This makes the mock axis match what the real `get_calibration` returns. This logic is specific to the mock version and is unrelated to the laser wavelength.
