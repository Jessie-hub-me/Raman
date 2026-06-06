# -*- coding: utf-8 -*-
"""
Created on Wed Apr 29 21:01:35 2026

@author: zhy86
"""

# -*- coding: utf-8 -*-

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
        prominence=prominence, # Only peaks that are 500 units higher than their surroundings are recorded; the default value is 500.
        distance=distance # Prevent multiple small noise spikes from being marked repeatedly at the peak of the same broad peak
    )
    
    peak_wavelengths = wavelengths[peaks_idx]
    peak_intensities = spectrum[peaks_idx]
    
    return peak_wavelengths, peak_intensities, peaks_idx


# def full_preprocessing_ramanspy(wavelengths, spectrum):
#     raman_spectrum = rp.Spectrum(spectrum, wavelengths)
    
#     pipeline = rp.preprocessing.Pipeline([
#         rp.preprocessing.baseline.DRPLS(lam=100000.0, eta=0.5),
#         rp.preprocessing.normalise.MinMax()
#     ])
    
#     processed = pipeline.apply(raman_spectrum)
    
#     return processed.spectral_data

# baseline correction
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


    #Input: spectra = [spectrum1, spectrum2, ...], Output: average spectrum


    if len(spectra) == 0:
        return None

    return np.mean(spectra, axis=0)


# Wavelength to Raman shift
def wavelength_to_raman(wavelengths, laser_wavelength):
    wavelengths = np.array(wavelengths) #nm

    raman_shift = (1/laser_wavelength - 1/wavelengths) * 1e7

    return raman_shift #(cm⁻¹)


def _voigt_single(x, amplitude, center, sigma, gamma, offset):
    return amplitude * voigt_profile(x - center, sigma, gamma) + offset


def fit_voigt_peak(x, y, center_guess, window=40.0):
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

    # The classical approximation for Voigt FWHM (Olivero & Longbothum 1977), with an error of <0.02%
    fwhm_g = 2.0 * sigma * np.sqrt(2.0 * np.log(2.0))   # Gaussian component FWHM
    fwhm_l = 2.0 * gamma                                # Lorentz component FWHM
    fwhm = 0.5346 * fwhm_l + np.sqrt(0.2166 * fwhm_l**2 + fwhm_g**2)

    # Peak height = peak of the fitted curve – offset
    height = amplitude * voigt_profile(0.0, sigma, gamma)
    # Area = amplitude
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
    #Performs a Voigt fit on each peak in a set.
    #x, y   : Raman shift (cm⁻¹), intensity (baseline-subtracted/unnormalized)
    # centers: List of initial peak centers (cm⁻¹)
    # Returns a list of dictionaries containing the results of successful fits (sorted by center).
    results = []
    for c in centers:
        r = fit_voigt_peak(x, y, c, window=window)
        if r is not None:
            results.append(r)
    results.sort(key=lambda d: d["center"])
    return results