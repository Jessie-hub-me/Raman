# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 16:03:13 2026

@author: zhy86
"""

import time
import numpy as np
import pylablib as pll
from pylablib.devices import Andor


pll.par["devices/dlls/andor_sdk2"] = "C:/Users/jeohlab/Desktop/Jessie/dlls/"
pll.par["devices/dlls/andor_shamrock"] = "C:/Users/jeohlab/Desktop/Jessie/dlls/"


class SpectrometerDevice:

    def __init__(self, initial_center_nm=600.0):

        print("Initializing spectrometer hardware...")

        # 打开 CCD 相机
        self.cam = Andor.AndorSDK2Camera()

        # 打开 spectrograph
        self.spec = Andor.ShamrockSpectrograph()

        # 根据 CCD 设置 pixel
        self.spec.setup_pixels_from_camera(self.cam)

        # 设置初始中心波长
        self.center_wavelength_nm = initial_center_nm
        self.spec.set_wavelength(initial_center_nm * 1e-9)
        time.sleep(1)

        # 获取波长校准
        self.wavelengths = self.spec.get_calibration()

        print(f"Center wavelength: {initial_center_nm} nm")
        print(f"Wavelength range: {self.wavelengths.min()*1e9:.1f} - "
              f"{self.wavelengths.max()*1e9:.1f} nm")
        print("Spectrometer initialization complete")


    def set_center_wavelength(self, wavelength_nm):
        try:
            self.spec.set_wavelength(wavelength_nm * 1e-9)
            time.sleep(1)
            self.wavelengths = self.spec.get_calibration()
            self.center_wavelength_nm = wavelength_nm
            print(f"Center wavelength set to {wavelength_nm} nm")
            print(f"Wavelength range: {self.wavelengths.min()*1e9:.1f} - "
                  f"{self.wavelengths.max()*1e9:.1f} nm")
            return True
        
        except Exception as e:
            print("Set center wavelength error:", e)
            return False


    def set_exposure(self, exposure):
        try:
            self.cam.set_exposure(exposure)  # unit: second
        except Exception as e:
            print("Exposure set error:", e)

    def get_spectrum(self):
        try:
            image = self.cam.snap()
            spectrum = image[0]
            return spectrum
        except Exception as e:
            print("Spectrum acquisition error:", e)
            return np.zeros(len(self.wavelengths))

    def get_temperature(self):
        try:
            temp = self.cam.get_temperature()
            return temp
        except Exception as e:
            print("Temperature read error:", e)
            return None

    def set_cooler(self, state):
        try:
            self.cam.set_cooler(state)
        except Exception as e:
            print("Cooler control error:", e)

    def close(self):
        print("Closing spectrometer hardware...")
        try:
            self.cam.close()
            print("Camera closed")
        except:
            print("Camera already closed")
        try:
            self.spec.close()
            print("Spectrograph closed")
        except:
            print("Spectrograph already closed")