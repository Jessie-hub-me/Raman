# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 20:07:57 2026

@author: zhy86
"""

import numpy as np

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QSpinBox, QCheckBox, 
                             QHBoxLayout
)

from PyQt5.QtCore import QTimer

import pyqtgraph as pg

from spectrometer_device import SpectrometerDevice
from spectrometer_processing import average_spectra


class SpectrometerGUI(QWidget):

    def __init__(self):

        super().__init__()

        print("Starting GUI...")

        # Device layer, connect to spectrometer_device.py
        self.device = SpectrometerDevice()

        self.wavelengths = self.device.wavelengths
        
        # Initial state variables
        self.last_spectrum = None # haven't get spectrum yet
        self.running = False # now not running
        
        # acquisition buffer
        self.spectra_buffer = []
        self.target_averages = 1

        self.init_ui()

        # temperature timer
        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_temperature)
        self.temp_timer.start(5000) # 5s

        # acquisition timer, Real-time spectral acquisition
        self.acquire_timer = QTimer()
        self.acquire_timer.timeout.connect(self.acquire_spectrum)
        
        # shutdown timer (used when closing GUI)
        self.shutdown_timer = QTimer()
        self.shutdown_timer.timeout.connect(self.check_shutdown_temperature)

    # Init GUI
    def init_ui(self):

        self.setWindowTitle("Raman Spectrometer Control")

        layout = QVBoxLayout()


        # Integration time, Horizontal arrangment
        exp_layout = QHBoxLayout()
        
        exp_label = QLabel("Integration Time (ms)")

        self.integration_spin = QSpinBox()
        self.integration_spin.setRange(1, 10000)
        self.integration_spin.setValue(100) #Default value 100ms

        exp_layout.addWidget(exp_label)
        exp_layout.addWidget(self.integration_spin)

        layout.addLayout(exp_layout) #add "Integration time" to layout

        # Averages
        avg_layout = QHBoxLayout()

        avg_label = QLabel("Averages")

        self.avg_spin = QSpinBox()
        self.avg_spin.setRange(1, 100)
        self.avg_spin.setValue(1)

        avg_layout.addWidget(avg_label)
        avg_layout.addWidget(self.avg_spin)

        layout.addLayout(avg_layout)

        # Overlay checkbox

        self.overlay_checkbox = QCheckBox("Overlay previous spectrum")
        layout.addWidget(self.overlay_checkbox)


        # # Start / Stop buttons
        # button_layout = QHBoxLayout()

        # self.start_button = QPushButton("Start Acquisition")
        # self.stop_button = QPushButton("Stop")

        # self.start_button.clicked.connect(self.start_acquisition)
        # self.stop_button.clicked.connect(self.stop_acquisition)

        # button_layout.addWidget(self.start_button)
        # button_layout.addWidget(self.stop_button)

        # layout.addLayout(button_layout)

        # Temperature label
        self.temp_label = QLabel("Temperature: -- °C")
        layout.addWidget(self.temp_label)
        
        self.get_button = QPushButton("Get Spectrum")
        self.get_button.clicked.connect(self.get_single_spectrum)

        layout.addWidget(self.get_button)

        # Spectrum Plot, pyqtgraph
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        self.curve = self.plot_widget.plot(pen='y') # yellow line
        # to create two curve in "plot_widget" window
        self.overlay_curve = self.plot_widget.plot(pen='w') # white line

        self.plot_widget.setLabel("left", "Intensity")
        self.plot_widget.setLabel("bottom", "Wavelength (nm)")

        self.setLayout(layout)


    def start_acquisition(self):

        print("Starting acquisition")

        exposure = self.integration_spin.value() / 1000 # Convert to second
        self.device.set_exposure(exposure)

        self.running = True

        # self.acquire_timer.start(2000) # acquire spectrum every 2 second

    def stop_acquisition(self):

        print("Stopping acquisition")

        self.running = False
        # self.acquire_timer.stop()

    # Acquire Spectrum every 2s
    # def acquire_spectrum(self):

    #     if not self.running:
    #         return

    #     averages = self.avg_spin.value()

    #     spectra = []

    #     for _ in range(averages):
    #         spectrum = self.device.get_spectrum()
    #         spectra.append(spectrum)

    #     spectrum = average_spectra(spectra)

    #     self.curve.setData(
    #         self.wavelengths * 1e9,
    #         spectrum
    #     )

    #     # overlay previous
    #     if self.overlay_checkbox.isChecked() and self.last_spectrum is not None:

    #         self.overlay_curve.setData(
    #             self.wavelengths * 1e9,
    #             self.last_spectrum
    #         )

    #     self.last_spectrum = spectrum
    
    def get_single_spectrum(self):

        print("Starting averaged acquisition...")
        # Avoid Continuously click Get Spectrum
        if self.acquire_timer.isActive():
            print("Acquisition already running")
            return

        exposure = self.integration_spin.value() / 1000
        self.device.set_exposure(exposure)

        # spectrum = self.device.get_spectrum()

        # # plot current spectrum
        # self.curve.setData(
        #     self.wavelengths * 1e9,
        #     spectrum
        # )

        # # overlay previous spectrum
        # if self.overlay_checkbox.isChecked() and self.last_spectrum is not None:

        #     self.overlay_curve.setData(
        #         self.wavelengths * 1e9,
        #         self.last_spectrum
        #         )

        # # 保存为 last spectrum
        # self.last_spectrum = spectrum
        # number of spectra to average
        self.target_averages = self.avg_spin.value()

        # clear buffer
        self.spectra_buffer = []

        # start timer= exposure time + 50ms
        interval = self.integration_spin.value() + 50
        self.acquire_timer.start(interval)
        
    def acquire_spectrum(self):

        spectrum = self.device.get_spectrum()

        self.spectra_buffer.append(spectrum)

        print(f"Collected {len(self.spectra_buffer)}/{self.target_averages}")

        avg_spectrum = average_spectra(self.spectra_buffer)

        # plot averaged spectrum
        self.curve.setData(
            self.wavelengths * 1e9,
            avg_spectrum
        )
        # if enough spectra collected
        if len(self.spectra_buffer) >= self.target_averages:

            self.acquire_timer.stop()



        # overlay previous spectrum
            if self.overlay_checkbox.isChecked() and self.last_spectrum is not None:

                self.overlay_curve.setData(
                    self.wavelengths * 1e9,
                    self.last_spectrum
                )

            # save for next overlay
            self.last_spectrum = avg_spectrum

            print("Averaged spectrum acquired.")

    def update_temperature(self):

        try:

            temp = self.device.get_temperature()

            self.temp_label.setText(
                f"Temperature: {temp:.2f} °C"
            )

        except:
            print("Temperature read error")
            
    def check_shutdown_temperature(self):
    
        try:
            temp = self.device.get_temperature()
            print(f"CCD temperature: {temp:.2f} °C")
    
            if temp > 0:
    
                print("CCD warmed up. Safe to close.")
    
                self.shutdown_timer.stop()
    
                print("Closing spectrometer hardware...")
                self.device.close()
    
                # 直接退出 GUI
                from PyQt5.QtWidgets import QApplication
                QApplication.quit()
    
        except:
            print("Temperature read error during shutdown")


    # def closeEvent(self, event):

    #     print("Closing system")

    #     try:
    #         self.acquire_timer.stop()
    #     except:
    #         pass

    #     try:
    #         self.temp_timer.stop()
    #     except:
    #         pass

    #     self.device.close()

    #     event.accept()
    
    def closeEvent(self, event):

        print("Shutting down spectrometer...")

        try:
            self.acquire_timer.stop()
        except:
            pass

        try:
            self.temp_timer.stop()
        except:
            pass

        try:

            print("Turning cooler off...")
            self.device.set_cooler(False)

            print("Waiting for CCD to warm up...")

            # start monitoring temperature
            self.shutdown_timer.start(5000)

            # prevent GUI from closing immediately
            event.ignore()

        except:

            print("Error during shutdown, closing device directly")

            self.device.close()
            event.accept()
            
            
            
            
if __name__ == "__main__":

    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    window = SpectrometerGUI()
    window.show()

    sys.exit(app.exec_())
