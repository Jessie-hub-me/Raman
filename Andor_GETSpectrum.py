# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 15:53:00 2026

@author: zhy86
"""

import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QLabel
)
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
from pylablib.devices import Andor
import time


class SpectrometerGUI(QWidget):

    def __init__(self):
        super().__init__()

        # 初始化
        self.cam = Andor.AndorSDK2Camera()
        self.spec = Andor.ShamrockSpectrograph()

        self.spec.set_wavelength(600e-9) #532e-9
        self.spec.setup_pixels_from_camera(self.cam)
        time.sleep(1)

        self.wavelengths = self.spec.get_calibration()
        self.cam.set_image_mode("fvb")

        # GUI
        self.setWindowTitle("Raman Spectrometer Control")

        self.layout = QVBoxLayout()

        self.button = QPushButton("Get Spectrum")
        self.button.clicked.connect(self.acquire_spectrum)
        self.layout.addWidget(self.button)

        self.temp_label = QLabel("Temperature: -- °C")
        self.layout.addWidget(self.temp_label)

        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)

        self.setLayout(self.layout)

        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_temperature)
        self.timer.start(1000)

    # 采集
    def acquire_spectrum(self):

        spectrum = self.cam.snap()[0]

        self.plot_widget.clear()
        self.plot_widget.plot(
            self.wavelengths * 1e9,
            spectrum,
            pen='y'
        )

    # 温度
    def update_temperature(self):

        temp = self.cam.get_temperature()
        self.temp_label.setText(f"Temperature: {temp:.2f} °C")


if __name__ == "__main__": #只有直接运行这个文件才执行下面代码
    app = QApplication(sys.argv) # 创建Qt应用
    window = SpectrometerGUI() # 创建窗口实例
    window.show() # 显示窗口
    sys.exit(app.exec_()) # 启动事件循环