# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 21:04:12 2026
@author: zhy86
"""

import numpy as np
import ramanspy as rp
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from scipy.special import voigt_profile


# Use SciPy to find peak positions and return the wavelength and intensity of the peaks
def find_peaks_in_spectrum(wavelengths, spectrum, height=None, prominence=500, distance=10):
    peaks_idx, properties = find_peaks(
        spectrum,
        height=height,
        prominence=prominence,
        distance=distance
    )
    peak_wavelengths = wavelengths[peaks_idx]
    peak_intensities = spectrum[peaks_idx]
    return peak_wavelengths, peak_intensities, peaks_idx


# def full_preprocessing_ramanspy(wavelengths, spectrum):
#     raman_spectrum = rp.Spectrum(spectrum, wavelengths)
#     pipeline = rp.preprocessing.Pipeline([
#         rp.preprocessing.baseline.IRSQR(lam=30, quantile=0.01, num_knots=50),
#         rp.preprocessing.normalise.MinMax()
#     ])
#     processed = pipeline.apply(raman_spectrum)
#     return processed.spectral_data


# baseline correction
# IRSQR（Iterative Reweighted Spline Quantile Regression），
# Data sourced from Optimal rows from the grid search in irsqr_tuning.csv
# These parameters are adjusted from the original data. If the actual sample has a broad fluorescent background,
# A larger lam value (stiffer baseline) may be required. 
def baseline_correction(wavelengths, spectrum):
    raman_spectrum = rp.Spectrum(spectrum, wavelengths)
    pipeline = rp.preprocessing.Pipeline([
        rp.preprocessing.baseline.IRSQR(lam=30, quantile=0.01, num_knots=50),
    ])
    processed = pipeline.apply(raman_spectrum)
    return processed.spectral_data


# normalization
def normalize_spectrum(wavelengths, spectrum):
    raman_spectrum = rp.Spectrum(spectrum, wavelengths)
    pipeline = rp.preprocessing.Pipeline([
        rp.preprocessing.normalise.MinMax()
    ])
    processed = pipeline.apply(raman_spectrum)
    return processed.spectral_data


# Average spectra
def average_spectra(spectra):
    if len(spectra) == 0:
        return None
    return np.mean(spectra, axis=0)


# Wavelength -> Raman shift
def wavelength_to_raman(wavelengths, laser_wavelength):
    """(nm) -> Raman shift(cm⁻¹)。"""
    wavelengths = np.array(wavelengths)  # nm
    raman_shift = (1.0 / laser_wavelength - 1.0 / wavelengths) * 1e7  # cm⁻¹
    return raman_shift


def _voigt_single(x, amplitude, center, sigma, gamma, offset):
    """Single Voigt peak + constant baseline."""
    return amplitude * voigt_profile(x - center, sigma, gamma) + offset


def fit_voigt_peak(x, y, center_guess, window=40.0):
    """Perform a Voigt fit on a single peak using only data within the range of `center_guess ± window`.

    Parameter Description:
    x, y: Raman shift (cm⁻¹) and intensity (subtracted baseline/unnormalized)
    center_guess: Initial peak center (cm⁻¹), typically obtained from `find_peaks`
    window: Local fitting half-width (cm⁻¹). A smaller window is used for closely spaced peaks to prevent interference.

    Returns:
    dict or None. On success, contains:
      center, fwhm, fwhm_g, fwhm_l, area, height, amplitude,
      sigma, gamma, offset, x_fit, y_fit (for plotting the fit curve), success=True
    Returns None on failure.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    mask = (x >= center_guess - window) & (x <= center_guess + window)
    if np.count_nonzero(mask) < 6:
        return None
    xw = x[mask]
    yw = y[mask]

    offset0 = float(np.min(yw))
    height0 = float(np.max(yw) - offset0)
    if height0 <= 0:
        return None
    # Estimate the initial width using half the height and width
    half = offset0 + height0 / 2.0
    above = xw[yw >= half]
    fwhm0 = (above.max() - above.min()) if above.size >= 2 else window / 2.0
    fwhm0 = max(fwhm0, 2.0)
    # Divide fwhm0 equally between sigma and gamma as initial values
    sigma0 = fwhm0 / 3.6
    gamma0 = fwhm0 / 3.6
    # Initial amplitude value: Set the peak to approximately height0. The peak of voigt_profile(0,σ,γ) needs to be converted,
    # Simply use height0 multiplied by an approximate coefficient; curve_fit will adjust itself accordingly.
    amp0 = height0 * (sigma0 + gamma0) * 2.0

    p0 = [amp0, center_guess, sigma0, gamma0, offset0]
    # Boundaries: amplitude > 0, center within the window, width > 0
    bounds = (
        [0.0,        center_guess - window, 1e-3, 1e-3, -np.inf],
        [np.inf,     center_guess + window, window, window,  np.inf],
    )

    try:
        popt, pcov = curve_fit(_voigt_single, xw, yw, p0=p0,
                               bounds=bounds, maxfev=10000)
    except Exception:
        return None

    amplitude, center, sigma, gamma, offset = popt

    fwhm_g = 2.0 * sigma * np.sqrt(2.0 * np.log(2.0))
    fwhm_l = 2.0 * gamma
    fwhm = 0.5346 * fwhm_l + np.sqrt(0.2166 * fwhm_l**2 + fwhm_g**2)

    # Peak height = peak of the fitted curve – offset
    height = amplitude * voigt_profile(0.0, sigma, gamma)
    # Area = amplitude (the Voigt profile is normalized, with an integral of 1, so the area is equal to the amplitude)
    area = amplitude

    # Dense sampling for fitting curves
    x_fit = np.linspace(xw.min(), xw.max(), 200)
    y_fit = _voigt_single(x_fit, *popt)

    return {
        "center": float(center),
        "fwhm": float(fwhm),
        "fwhm_g": float(fwhm_g),
        "fwhm_l": float(fwhm_l),
        "area": float(area),
        "height": float(height),
        "amplitude": float(amplitude),
        "sigma": float(sigma),
        "gamma": float(gamma),
        "offset": float(offset),
        "x_fit": x_fit,
        "y_fit": y_fit,
        "success": True,
    }


def fit_voigt_peaks(x, y, centers, window=40.0):
    """Perform Voigt fitting on a set of peaks one by one.

    x, y: Raman shift (cm⁻¹), intensity (baseline-subtracted/unnormalized)
    centers: List of initial peak centers (cm⁻¹)
    Returns:
    a list of dictionaries containing the results of successful fits (sorted by center).
    """
    results = []
    for c in centers:
        r = fit_voigt_peak(x, y, c, window=window)
        if r is not None:
            results.append(r)
    results.sort(key=lambda d: d["center"])
    return results