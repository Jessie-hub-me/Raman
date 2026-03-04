# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 16:54:24 2026

@author: jeohlab
"""


import pylablib as pll
from pylablib.devices import Andor
import numpy as np
import matplotlib.pyplot as plt
import time

# 如果需要指定 DLL 路径，
pll.par["devices/dlls/andor_sdk2"] = "C:/Users/jeohlab/Desktop/Jessie/dlls/"
pll.par["devices/dlls/andor_shamrock"] = "C:/Users/jeohlab/Desktop/Jessie/dlls/"

#打开 camera
cam = Andor.AndorSDK2Camera()
print("Camera OK")
time.sleep(1)


#打开 spectrograph
spec = Andor.ShamrockSpectrograph()
print("Spectrograph OK")
time.sleep(1)


#设置中心波长
spec.set_wavelength(600e-9)

#让 spectrograph 读取 camera 像素结构
spec.setup_pixels_from_camera(cam) #把 CCD 的像素结构信息 告诉光谱仪
time.sleep(1)

#获取波长标定
wavelengths = spec.get_calibration() #计算每一个 CCD 像素对应的真实波长
time.sleep(1)

#设置 FVB 模式
#cam.set_image_mode("fvb")
#time.sleep(1)

#获取光谱
spectrum = cam.snap()[0]

#plot
plt.plot(wavelengths * 1e9, spectrum)
plt.xlabel("Wavelength (nm)")
plt.ylabel("Intensity")
plt.show()

#close
cam.close()
spec.close()

print("Connection Closed")
