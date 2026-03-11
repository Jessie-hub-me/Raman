# -*- coding: utf-8 -*-
"""
Created on Sat Mar  7 15:43:55 2026

@author: zhy86
"""

# -*- coding: utf-8 -*-

import numpy as np



# Average spectra
def average_spectra(spectra):


    #输入:spectra = [spectrum1, spectrum2, ...],输出:平均光谱


    if len(spectra) == 0:
        return None

    return np.mean(spectra, axis=0)


# Normalize spectrum

def normalize_spectrum(spectrum):

    """
    归一化光谱
    """

    spectrum = np.array(spectrum)

    max_val = np.max(spectrum)

    if max_val == 0:
        return spectrum

    return spectrum / max_val


# Wavelength → Raman shift
def wavelength_to_raman(wavelengths, laser_wavelength):

    """
    波长转换为 Raman shift

    输入
        wavelengths: nm
        laser_wavelength: nm

    输出
        Raman shift (cm⁻¹)
    """

    wavelengths = np.array(wavelengths)

    raman_shift = (1/laser_wavelength - 1/wavelengths) * 1e7

    return raman_shift


# Simple smoothing (moving average)

def smooth_spectrum(spectrum, window=5):

    """
    简单滑动平均平滑
    """

    spectrum = np.array(spectrum)

    kernel = np.ones(window) / window

    smooth = np.convolve(spectrum, kernel, mode='same')

    return smooth