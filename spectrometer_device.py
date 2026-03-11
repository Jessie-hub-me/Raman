# -*- coding: utf-8 -*-
"""
Created on Sat Mar  7 15:41:03 2026

@author: zhy86
"""

# -*- coding: utf-8 -*-

import time
import numpy as np
import pylablib as pll
from pylablib.devices import Andor


pll.par["devices/dlls/andor_sdk2"] = "C:/Users/jeohlab/Desktop/Jessie/dlls/"
pll.par["devices/dlls/andor_shamrock"] = "C:/Users/jeohlab/Desktop/Jessie/dlls/"

class SpectrometerDevice:

    def __init__(self):

        print("Initializing spectrometer hardware...")

        # 打开 CCD 相机
        self.cam = Andor.AndorSDK2Camera()

        # 打开 spectrograph
        self.spec = Andor.ShamrockSpectrograph()

        # 设置中心波长
        self.spec.set_wavelength(600e-9)

        # 根据 CCD 设置 pixel
        self.spec.setup_pixels_from_camera(self.cam)

        time.sleep(1)

        # 获取波长校准
        self.wavelengths = self.spec.get_calibration()

        # FVB 模式
        # self.cam.set_image_mode("fvb")

        print("Spectrometer initialization complete")

    # Set CCD integration time
    def set_exposure(self, exposure):

        try:

            self.cam.set_exposure(exposure) # unit: second

        except Exception as e:

            print("Exposure set error:", e)



    def get_spectrum(self):
        try:

            image = self.cam.snap()

            spectrum = image[0]

            return spectrum

        except Exception as e:

            print("Spectrum acquisition error:", e)

            return np.zeros(len(self.wavelengths)) # if error:return all zero spectrum

    def get_temperature(self):
        try:

            temp = self.cam.get_temperature()

            return temp

        except Exception as e:

            print("Temperature read error:", e)

            return None


    def close(self):

        print("Closing spectrometer hardware...")

        # 关闭 camera
        try:

            self.cam.close()

            print("Camera closed")

        except:

            print("Camera already closed")

        # 关闭 spectrograph
        try:

            self.spec.close()

            print("Spectrograph closed")

        except:

            print("Spectrograph already closed")