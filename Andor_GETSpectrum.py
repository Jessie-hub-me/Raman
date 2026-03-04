# -*- coding: utf-8 -*-
"""
Created on Tue Mar  3 15:53:00 2026

@author: zhy86
"""
# -*- coding: utf-8 -*-


import sys
import numpy as np
import time

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel
)

from PyQt5.QtCore import QTimer
import pyqtgraph as pg

from pylablib.devices import Andor


class SpectrometerGUI(QWidget):

    def __init__(self):
        super().__init__()

        print("Initializing devices...")

        # 打开 CCD
        self.cam = Andor.AndorSDK2Camera()

        # 打开 spectrograph
        self.spec = Andor.ShamrockSpectrograph()

        # 设置中心波长
        self.spec.set_wavelength(600e-9)

        # 读取像素结构
        self.spec.setup_pixels_from_camera(self.cam)

        time.sleep(1)

        # 获取波长校准
        self.wavelengths = self.spec.get_calibration()

        # FVB模式
        #self.cam.set_image_mode("fvb")

        print("Initialization complete")

        # ---------------- GUI ----------------

        self.setWindowTitle("Raman Spectrometer Control")

        self.layout = QVBoxLayout()

        # 获取光谱按钮
        self.button = QPushButton("Get Spectrum")
        self.button.clicked.connect(self.acquire_spectrum)
        self.layout.addWidget(self.button)

        # 温度显示
        self.temp_label = QLabel("Temperature: -- °C")
        self.layout.addWidget(self.temp_label)

        # plot窗口
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)

        self.setLayout(self.layout)

        # ---------------- 定时器 ----------------

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_temperature)
        self.timer.start(1000)

    # ---------------- 获取光谱 ----------------

    def acquire_spectrum(self):

        print("Acquiring spectrum...")

        spectrum = self.cam.snap()[0]

        self.plot_widget.clear()

        self.plot_widget.plot(
            self.wavelengths * 1e9,
            spectrum,
            pen='y'
        )

    # ---------------- 更新温度 ----------------

    def update_temperature(self):

        try:
            temp = self.cam.get_temperature()
            self.temp_label.setText(f"Temperature: {temp:.2f} °C")

        except:
            print("Temperature read error")

    # ---------------- 关闭GUI时关闭设备 ----------------

    def closeEvent(self, event):

        print("Closing spectrometer system...")

        # 停止timer
        try:
            self.timer.stop()
        except:
            pass

        # 关闭camera
        try:
            self.cam.close()
            print("Camera closed")
        except:
            print("Camera already closed")

        # 关闭spectrograph
        try:
            self.spec.close()
            print("Spectrograph closed")
        except:
            print("Spectrograph already closed")

        event.accept()


# ---------------- 主程序 ----------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = SpectrometerGUI()
    window.show()

    sys.exit(app.exec_())