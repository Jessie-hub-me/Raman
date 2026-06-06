# -*- coding: utf-8 -*-
"""
Created on Thu Apr 30 15:50:41 2026

@author: zhy86
"""

import numpy as np

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QSpinBox, QCheckBox, 
                             QHBoxLayout, QDoubleSpinBox
)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

import pyqtgraph as pg

from spectrometer_device_mock_calibrate import SpectrometerDevice
from spectrometer_processing_mock_calibrate import (
    average_spectra, find_peaks_in_spectrum,  baseline_correction, normalize_spectrum,
    wavelength_to_raman, fit_voigt_peaks
)
from PyQt5.QtWidgets import QComboBox, QTextEdit
import datetime 


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
        
        self.allow_exit = False
        
        self.current_raw_spectrum = None
        self.last_raw_spectrum = None 
        self.history_spectra = [] 
        # {"time": "14:20:01", "data": array, "wavelengths": array}

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

        # === MOCK MODE: file selector for test data ===
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Test File"))
        self.file_combo = QComboBox()
        self.file_combo.addItems(self.device.list_files())
        self.file_combo.currentIndexChanged.connect(self.on_file_changed)
        file_layout.addWidget(self.file_combo)
        layout.addLayout(file_layout)
        # === end mock-mode block ===

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
        
        
        
        processing_layout = QHBoxLayout()
        
        self.baseline_checkbox = QCheckBox("Baseline Correction")
        self.normalize_checkbox = QCheckBox("Normalize")
        self.peak_finder_checkbox = QCheckBox("Peak Finder")
        self.raman_shift_checkbox = QCheckBox("Raman Shift")

        processing_layout.addWidget(self.baseline_checkbox)
        processing_layout.addWidget(self.normalize_checkbox)
        processing_layout.addWidget(self.peak_finder_checkbox)
        processing_layout.addWidget(self.raman_shift_checkbox)
        
        layout.addLayout(processing_layout)
        
        peak_param_layout = QHBoxLayout()
        peak_param_layout.addWidget(QLabel("Prominence"))
        
        self.prominence_spin = QDoubleSpinBox()
        self.prominence_spin.setRange(0.0, 100000.0)
        self.prominence_spin.setSingleStep(0.01)
        self.prominence_spin.setDecimals(3)
        self.prominence_spin.setValue(500.0)
    
        
        peak_param_layout.addWidget(self.prominence_spin)
        layout.addLayout(peak_param_layout)
        
        self.peak_scatter = pg.ScatterPlotItem(
            size=10,  
            pen=pg.mkPen('r'), 
            brush=pg.mkBrush('r') 
        )
        self.plot_widget.addItem(self.peak_scatter)


        self.fit_curves = []
        
        self.history_combo = QComboBox()
        self.history_combo.addItem("Last Spectrum") 

        layout.addWidget(QLabel("Compare with:"))
        layout.addWidget(self.history_combo)
        
        # Center wavelength control
        center_layout = QHBoxLayout()
        center_layout.addWidget(QLabel("Center Wavelength (nm)"))
        
        self.center_spin = QDoubleSpinBox()
        self.center_spin.setRange(200.0, 1200.0)
        self.center_spin.setDecimals(1)
        self.center_spin.setSingleStep(1.0)
        self.center_spin.setValue(532.0)
        center_layout.addWidget(self.center_spin)
        
        self.apply_center_button = QPushButton("Apply")
        self.apply_center_button.clicked.connect(self.apply_center_wavelength)
        center_layout.addWidget(self.apply_center_button)
        
        layout.addLayout(center_layout)
        
        laser_layout = QHBoxLayout()
        laser_layout.addWidget(QLabel("Laser (nm)"))
        self.laser_spin = QDoubleSpinBox()
        self.laser_spin.setRange(200.0, 1200.0)
        self.laser_spin.setDecimals(2) 
        self.laser_spin.setSingleStep(0.1)
        self.laser_spin.setValue(532.0) 
        laser_layout.addWidget(self.laser_spin)
        layout.addLayout(laser_layout)

        range_layout = QHBoxLayout()
        self.limit_range_checkbox = QCheckBox("Limit X range")
        self.limit_range_checkbox.setChecked(True) 
        range_layout.addWidget(self.limit_range_checkbox)

        range_layout.addWidget(QLabel("min"))
        self.xmin_spin = QDoubleSpinBox()
        self.xmin_spin.setRange(-5000.0, 5000.0)
        self.xmin_spin.setDecimals(0)
        self.xmin_spin.setSingleStep(50.0)
        self.xmin_spin.setValue(100.0)
        range_layout.addWidget(self.xmin_spin)

        range_layout.addWidget(QLabel("max"))
        self.xmax_spin = QDoubleSpinBox()
        self.xmax_spin.setRange(-5000.0, 5000.0)
        self.xmax_spin.setDecimals(0)
        self.xmax_spin.setSingleStep(50.0)
        self.xmax_spin.setValue(1300.0)
        range_layout.addWidget(self.xmax_spin)

        layout.addLayout(range_layout)

        self.fit_button = QPushButton("Fit Peaks (Voigt)")
        self.fit_button.clicked.connect(self.fit_peaks)
        layout.addWidget(self.fit_button)

        self.fit_result_text = QTextEdit()
        self.fit_result_text.setReadOnly(True)
        self.fit_result_text.setMaximumHeight(120)
        self.fit_result_text.setPlaceholderText(
            "After clicking Fit Peaks, results show each peak's center / FWHM / area"
        )
        layout.addWidget(self.fit_result_text)

        self.setLayout(layout)

        self.baseline_checkbox.stateChanged.connect(self.update_plot_display)
        self.normalize_checkbox.stateChanged.connect(self.update_plot_display)
        self.peak_finder_checkbox.stateChanged.connect(self.update_plot_display)
        self.prominence_spin.valueChanged.connect(self.update_plot_display)
        self.history_combo.currentIndexChanged.connect(self.update_plot_display)
        self.raman_shift_checkbox.stateChanged.connect(self.update_plot_display)
        self.laser_spin.valueChanged.connect(self.update_plot_display)
        self.limit_range_checkbox.stateChanged.connect(self.update_plot_display)
        self.xmin_spin.valueChanged.connect(self.update_plot_display)
        self.xmax_spin.valueChanged.connect(self.update_plot_display)
        

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
    
    def apply_center_wavelength(self):
        if self.acquire_timer.isActive():
            print("Acquisition in progress, please wait until it finishes.")
            return
        
        target_nm = self.center_spin.value()
        print(f"Applying new center wavelength: {target_nm} nm")
        
        success = self.device.set_center_wavelength(target_nm)
        if not success:
            print("Failed to set center wavelength. Keeping previous setting.")
            return

        self.wavelengths = self.device.wavelengths
        
        self.current_raw_spectrum = None
        self.last_raw_spectrum = None
        
        self.curve.clear()
        self.overlay_curve.clear()
        self.peak_scatter.clear()
        
        print("Center wavelength updated. Click Get Spectrum to acquire under new setting.")


    def _clear_fit_curves(self):
        for c in self.fit_curves:
            self.plot_widget.removeItem(c)
        self.fit_curves = []

    def fit_peaks(self):

        if self.current_raw_spectrum is None:
            self.fit_result_text.setText("No spectrum data. Please click Get Spectrum first.")
            return

        if not self.raman_shift_checkbox.isChecked():
            self.fit_result_text.setText(
                "Please enable Raman Shift first :Voigt widths are only meaningful on the cm⁻¹ axis."
            )
            return

        wavelengths_nm = self.wavelengths * 1e9

        try:
            y_bc = baseline_correction(wavelengths_nm, self.current_raw_spectrum)
            y_bc = np.asarray(y_bc).ravel()
        except Exception as e:
            self.fit_result_text.setText(f"Baseline correction failed: {e}")
            return

        laser_nm = self.laser_spin.value()
        x_cm = wavelength_to_raman(wavelengths_nm, laser_nm)

        try:
            p_wl, p_int, idx = find_peaks_in_spectrum(
                wavelengths_nm, y_bc, prominence=self.prominence_spin.value()
            )
        except Exception as e:
            self.fit_result_text.setText(f"Peak finding failed: {e}")
            return

        centers = x_cm[idx]
        centers = centers[(centers > 80) & (centers < 1400)]
        if len(centers) == 0:
            self.fit_result_text.setText("No peaks found to fit (try lowering Prominence).")
            return

        results = fit_voigt_peaks(x_cm, y_bc, centers, window=40.0)

        self._clear_fit_curves()
        for r in results:
            c = self.plot_widget.plot(
                r["x_fit"], r["y_fit"],
                pen=pg.mkPen('c', width=2) 
            )
            self.fit_curves.append(c)

        if not results:
            self.fit_result_text.setText("Fit did not converge. Try adjusting Prominence or check the data.")
            return

        lines = ["Voigt fit results (center / FWHM / area):"]
        for r in results:
            lines.append(
                f"  {r['center']:7.1f} cm⁻¹   FWHM={r['fwhm']:5.1f}   "
                f"area={r['area']:.3e}   height={r['height']:.0f}"
            )
        lines.append("（FWHM includes instrument broadening; fit on baseline-corrected, non-normalized data)")
        self.fit_result_text.setText("\n".join(lines))
        print("\n".join(lines))


    def update_plot_display(self):
        if self.current_raw_spectrum is None:
            return
        
        wavelengths_nm = self.wavelengths * 1e9
        
        # 决定 X 轴用什么
        if self.raman_shift_checkbox.isChecked():
            laser_nm = self.laser_spin.value()
            x_axis = wavelength_to_raman(wavelengths_nm, laser_nm)
            self.plot_widget.setLabel("bottom", "Raman Shift (cm⁻¹)")
        else:
            x_axis = wavelengths_nm
            self.plot_widget.setLabel("bottom", "Wavelength (nm)")
        
        current_display = self.apply_processing_to_data(
            wavelengths_nm, self.current_raw_spectrum, update_peaks=True
        )
        self.curve.setData(x_axis, current_display)

        try:
            use_limit = (self.limit_range_checkbox.isChecked()
                         and self.raman_shift_checkbox.isChecked())

            if use_limit:
                xlo = self.xmin_spin.value()
                xhi = self.xmax_spin.value()
                if xhi <= xlo:
                    use_limit = False

            if use_limit:
                mask = (x_axis >= xlo) & (x_axis <= xhi)
                if np.any(mask):
                    ywin = current_display[mask]
                    ymin = float(np.min(ywin))
                    ymax = float(np.max(ywin))
                    ypad = (ymax - ymin) * 0.05 if ymax > ymin else 1.0
                    self.plot_widget.setXRange(xlo, xhi, padding=0)
                    self.plot_widget.setYRange(ymin - ypad, ymax + ypad, padding=0)
                else:
                    use_limit = False       

            if not use_limit:
                ymin = float(np.min(current_display))
                ymax = float(np.max(current_display))
                ypad = (ymax - ymin) * 0.05 if ymax > ymin else 1.0
                self.plot_widget.setYRange(ymin - ypad, ymax + ypad, padding=0)
                self.plot_widget.setXRange(float(np.min(x_axis)), float(np.max(x_axis)),
                                           padding=0.02)
        except Exception as e:
            print("Auto-range warning:", e)


        if self.overlay_checkbox.isChecked():
            idx = self.history_combo.currentIndex()
            compare_raw = None
            compare_wavelengths_nm = None
            
            if idx == 0:
                compare_raw = self.last_raw_spectrum
                compare_wavelengths_nm = wavelengths_nm
            elif idx > 0:
                entry = self.history_spectra[idx - 1]
                compare_raw = entry["data"]
                compare_wavelengths_nm = entry["wavelengths"] * 1e9 
            
            if compare_raw is not None:
                compare_display = self.apply_processing_to_data(
                    compare_wavelengths_nm, compare_raw, update_peaks=False
                )

                if self.raman_shift_checkbox.isChecked():
                    compare_x = wavelength_to_raman(compare_wavelengths_nm, self.laser_spin.value())
                else:
                    compare_x = compare_wavelengths_nm
                self.overlay_curve.setData(compare_x, compare_display)
                self.overlay_curve.show()
            else:
                self.overlay_curve.hide()
        else:
            self.overlay_curve.hide()

    def apply_processing_to_data(self, wavelengths_nm, raw_data, update_peaks=False):

        processed = raw_data.copy()
        
        if self.baseline_checkbox.isChecked():
            processed = baseline_correction(wavelengths_nm, processed)
        
        if self.normalize_checkbox.isChecked():
            processed = normalize_spectrum(wavelengths_nm, processed)
            
        if update_peaks:
            self.peak_scatter.clear()
            self._clear_fit_curves() 
            if self.peak_finder_checkbox.isChecked():
                try:
                    p_wl, p_int, _ = find_peaks_in_spectrum(
                        wavelengths_nm, processed, prominence=self.prominence_spin.value()
                    )
                    if self.raman_shift_checkbox.isChecked():
                        laser_nm = self.laser_spin.value()
                        p_x = wavelength_to_raman(p_wl, laser_nm)
                    else:
                        p_x = p_wl
                    self.peak_scatter.setData(x=p_x.tolist(), y=p_int.tolist())
                except:
                    pass
                
        return processed
    
    
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
    
    
        if len(self.spectra_buffer) >= self.target_averages:
            self.acquire_timer.stop()
    
            new_raw = average_spectra(self.spectra_buffer)
            
            self.last_raw_spectrum = self.current_raw_spectrum 
            self.current_raw_spectrum = new_raw
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.history_spectra.append({"time": timestamp,
                "data": new_raw,
                "wavelengths": self.wavelengths.copy() 
            })
            self.history_combo.addItem(f"Spectrum {timestamp}")
            
            self.update_plot_display() 
            
            print("Averaged spectrum acquired and saved to history.")


    def on_file_changed(self, index):
        """MOCK: switch which .asc file get_spectrum() will return."""
        if self.device.load_file(index):

            self.wavelengths = self.device.wavelengths

            self.current_raw_spectrum = None
            self.last_raw_spectrum = None
            self.curve.clear()
            self.overlay_curve.clear()
            self.peak_scatter.clear()
            print("Test file switched. Click Get Spectrum to load it.")

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
                    

                    self.device.close()
                    
                    self.allow_exit = True
                    self.close() 
        
            except Exception as e:
                print(f"Temperature check error: {e}")
                self.device.close()
                self.allow_exit = True
                self.close()


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
            # MOCK MODE: There is no physical hardware to protect, so just turn it off.
            print("Closing (mock mode)...")
            try:
                self.acquire_timer.stop()
                self.temp_timer.stop()
            except:
                pass
            try:
                self.device.close()
            except:
                pass
            event.accept()
            
            
            
            
if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    window = SpectrometerGUI()
    window.show()

    sys.exit(app.exec_())