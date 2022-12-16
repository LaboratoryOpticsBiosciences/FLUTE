# Main function that runs the front UI, bot doesn't handle any of the data analysis, which is mainly handled by the
# ImageHandler class.

#imports
import sys
from sys import platform
from PyQt5 import QtWidgets
from PyQt5 import uic, QtCore
from PyQt5.QtCore import QPropertyAnimation, QRect, QEasingCurve, QTimer
from PyQt5.QtGui import QIcon, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QFileDialog
import DataWindows
import os
from ImageHandler import ImageHandler
import Calibration
import pickle
import numpy as np
import MplWidget
import range_slider

import ctypes
import platform

def make_dpi_aware():
    if int(platform.release()) >= 8:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)

dir_path = os.path.dirname(__file__)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. Important to keep track of files when
    compiling to a single file"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(QtWidgets.QMainWindow):
    """Main function that runs the front panel, and coordinates the user interactions with the images that they mean
    to be interacting with. All the buttons in the front panel are connected to their required functions here, and
    a list of images is used to keep track of which dataset the user is interacting with."""
    def __init__(self, *args, **kwargs):
        """Initialize the buttons and connect the signals"""
        super().__init__(*args, **kwargs)
        uic.loadUi(resource_path(dir_path + "/ui files/mainwindow.ui"), self)
        self.MoveFrame.clicked.connect(self.move_block)
        self.current_frame = self.MainFrame
        self.menu_size = 135
        self.menu_x = self.current_frame.x()
        self.save_type = 'all'
        self.LoadFLIM.clicked.connect(self.open_picture)
        self.LoadCalibr.clicked.connect(self.open_calibration)
        self.bulk_load.clicked.connect(self.bulk_open)

        self.HomeFrameButton.clicked.connect(lambda: self.change_frame(self.MainFrame))
        self.GraphButton.clicked.connect(lambda: self.change_frame(self.GraphFrame))
        self.PictureButton.clicked.connect(lambda: self.change_frame(self.PictureFrame))

        self.Phi_cal_box.setValidator(QDoubleValidator())
        self.Phi_cal_box.textEdited.connect(self.cal_update)
        self.m_cal_box.setValidator(QDoubleValidator())
        self.m_cal_box.textEdited.connect(self.cal_update)

        self.tableWidget.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.tableWidget.itemSelectionChanged.connect(self.setActive)

        self.circleSlider.setHigh(120)
        self.fractionSlider.setHigh(120)
        self.angleSlider.setHigh(90)
        self.angleSlider.sliderMoved.connect(self.update_angle_range)
        self.circleSlider.sliderMoved.connect(self.update_circle_range)
        self.fractionSlider.sliderMoved.connect(self.update_fraction_range)
        self.clearCircles.clicked.connect(self.clear_circles)
        self.SaveData.clicked.connect(self.save_data_popup)

        self.IntensityMin.returnPressed.connect(self.update_threshold)
        self.IntensityMin.setValidator(QIntValidator())
        self.IntensityMax.returnPressed.connect(self.update_threshold)
        self.IntensityMax.setValidator(QIntValidator())

        self.Phi_min.returnPressed.connect(self.phi_entry)
        self.Phi_min.setValidator(QDoubleValidator())
        self.Phi_max.returnPressed.connect(self.phi_entry)
        self.Phi_max.setValidator(QDoubleValidator())
        self.M_min.returnPressed.connect(self.M_entry)
        self.M_min.setValidator(QDoubleValidator())
        self.M_max.returnPressed.connect(self.M_entry)
        self.M_max.setValidator(QDoubleValidator())
        self.frac_min.returnPressed.connect(self.frac_entry)
        self.frac_min.setValidator(QDoubleValidator())
        self.frac_max.returnPressed.connect(self.frac_entry)
        self.frac_max.setValidator(QDoubleValidator())

        self.set_radius.returnPressed.connect(self.change_radius)

        self.ApplyFilter.clicked.connect(self.applyAllFilters)
        self.Filters.returnPressed.connect(self.applyFilter)
        self.Filters.setValidator(QIntValidator())

        self.Grey_Color.clicked.connect(lambda: self.set_colormap(0))
        self.TauM_Color.clicked.connect(lambda: self.set_colormap(1))
        self.TauP_Color.clicked.connect(lambda: self.set_colormap(2))
        self.Fraction_Color.clicked.connect(self.fraction_bound_color)

        self.reset_range.clicked.connect(self.reset_circles)
        self.close_selected.clicked.connect(self.CloseWindows)
        self.ShowRangeLines.clicked.connect(self.range_lines)

        # To make it easier to use the program, various parameters are saved from the last use, so that you don't need
        # to keep adding calibration parameters, or going to various directories each time
        if os.path.isfile('saved_dict.pkl'):
            with open('saved_dict.pkl', 'rb') as f:
                self.load_dict = pickle.load(f)
        else:
            self.load_dict = {'FLIM Load': '', "Cal Load": '', "Bin Width": 0.227, "Freq": 80.0, "Tau Ref": 4.0,
                              "Harmonic": 1.0, "Phi Cal": 0.0, "M Cal": 1.0,"Fraction": 0.4, "save_Dir": '', "FractionX": 1.0, "FractionY":0.0,
                              "framex": 611, "framey": 505, "table0Width": 290, "table1Width": 50, "table2Width": 143}
            with open('saved_dict.pkl', 'wb') as f:
                pickle.dump(self.load_dict, f)
        f.close()
        self.resize(self.load_dict['framex'], self.load_dict['framey'])
        self.tableWidget.setColumnWidth(0, self.load_dict['table0Width'])
        self.tableWidget.setColumnWidth(1, self.load_dict['table1Width'])
        self.tableWidget.setColumnWidth(2, self.load_dict['table2Width'])
        self.window_num = 1
        self.Phi_cal_box.setText("{:.4f}".format(self.load_dict['Phi Cal']))
        self.m_cal_box.setText("{:.4f}".format(self.load_dict['M Cal']))

        # Runs self.update on a timer, which checks if windows have been closed and closes their partner plots/windows
        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(10)

        # Keeps track of all the images that are opened
        self.image_arr = []

    def update(self):
        """Sets the colour of the circle for when the user clicks, and kills the parter windows/plots if the user
        closes a data window"""
        self.load_dict['table0Width'] = self.tableWidget.columnWidth(0)
        self.load_dict['table1Width'] = self.tableWidget.columnWidth(1)
        self.load_dict['table2Width'] = self.tableWidget.columnWidth(2)
        for idx, image in enumerate(self.image_arr):
            image.set_circle(self.circleSelect.currentIndex())
            if image.dead():
                del self.image_arr[idx]
                self.tableWidget.removeRow(idx)

    def open_picture(self):
        """ Opens the file dialog and loads the data if the user selects a tiff file"""
        file = QFileDialog.getOpenFileNames(self, 'Open file', str(self.load_dict['FLIM Load']), 'Tiff (*.tif *.tiff)')
        for data in file[0]:
            self.load_data(data)

    def range_lines(self):
        """Turns on and off the thresholding lines on the plot when you check ShowRangeLines on the window"""
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].show_lines(self.ShowRangeLines.isChecked())

    def bulk_open(self):
        """Opens a group of images, applies threshold, saves the data, and then closes the windows right away.
        Allows the user to open hundreds of images without hundreds of windows opening up and cluttering"""
        save_folder = ''
        file = QFileDialog.getOpenFileNames(self, 'Open file', str(self.load_dict['FLIM Load']), 'Tiff (*.tif *.tiff)')
        if file[0]: # make sure the user selected a piece of data
            save_folder = QFileDialog.getExistingDirectory(self, directory = self.load_dict['save_Dir'])
        if save_folder != '':
            for data in file[0]:
                self.load_data(data)
                self.save_selected_data(save_folder)
                selection = self.tableWidget.selectionModel().selectedRows()
                for i in selection:
                    self.image_arr[i.row()].kill()

    def load_data(self, file_name):
        """loads a picture from the file_name location, and populates the table widget"""
        self.load_dict['FLIM Load'] = os.path.dirname(file_name)
        # keep track of the image
        self.image_arr.append(ImageHandler(file_name, self.load_dict['Phi Cal'], self.load_dict['M Cal'],
                                           self.load_dict['Bin Width'], self.load_dict['Freq'],
                                           self.load_dict['Harmonic']))
        # bind the action when the user clicks the plot
        self.image_arr[-1].binding_id = \
            self.image_arr[-1].graph_window.Plot.canvas.mpl_connect('button_press_event', self.update_circle)
        name, dim = self.image_arr[-1].get_image_params()
        self.image_arr[-1].set_data_num(self.window_num)

        self.tableWidget.insertRow(self.tableWidget.rowCount())
        self.tableWidget.setItem(len(self.image_arr) - 1, 0, QtWidgets.QTableWidgetItem(name))
        self.tableWidget.setItem(len(self.image_arr) - 1, 1, QtWidgets.QTableWidgetItem(str(dim)))
        self.tableWidget.setItem(len(self.image_arr) - 1, 2, QtWidgets.QTableWidgetItem(str(self.window_num)))
        self.tableWidget.selectRow(len(self.image_arr) - 1)
        self.window_num = self.window_num + 1
        self.applyAllFilters()

    def update_circle(self, event):
        """Draws the circle on all active plots when the user clicks a plot that's active"""
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].update_circle(event)

    def open_calibration(self):
        """Opens the calibration window to let the user type in their parameters, and then runs loadCalibration() which
         calculates the values of Phi and M to translate the data by"""
        self.cal = DataWindows.Calibration()
        self.cal.Freq.setText(str(self.load_dict['Freq']))
        self.cal.bin_width.setText(str(self.load_dict['Bin Width']))
        self.cal.Tau.setText(str(self.load_dict['Tau Ref']))
        self.cal.Harmonic.setText(str(self.load_dict['Harmonic']))
        self.cal.show()
        self.cal.Cancel.clicked.connect(self.kill_cal)
        self.cal.LoadCalibr.clicked.connect(self.loadCalibration)

    def fraction_bound_color(self):
        """Opens the window to set the fraction bound parameter, such as 0.4ns for NADH. If the user clicks enter, this
        then changes the coordinates of the fraction bound circles to be centered on the lifetime selected
        by calling self.fraction_col_map()"""
        self.fraction = DataWindows.Fraction()
        self.fraction.lifetime.setText(str(self.load_dict["Fraction"]))
        self.fraction.x_coor.setText(str(self.load_dict["FractionX"]))
        self.fraction.y_coor.setText(str(self.load_dict["FractionY"]))
        self.fraction.lifetime.setValidator(QDoubleValidator())
        self.fraction.x_coor.setValidator(QDoubleValidator())
        self.fraction.y_coor.setValidator(QDoubleValidator())
        self.fraction.Cancel.clicked.connect(self.kill_fraction)
        self.fraction.EnterLifetime.clicked.connect(self.fraction_lifetime_map)
        self.fraction.EnterCoors.clicked.connect(self.fraction_coor_map)
        self.fraction.show()

    def fraction_lifetime_map(self):
        """Moves the location of the fraction bound circles to where the user selected based on lifetime"""
        lifetime = float(self.fraction.lifetime.text().replace(",",".").replace(",","."))
        self.load_dict["Fraction"] = lifetime
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].fraction_lifetime_map(lifetime)
        self.frac_entry()
        self.kill_fraction()

    def fraction_coor_map(self):
        """Moves the location of teh fraction bound circles to where the user selected based on coordinates"""
        x_coor = float(self.fraction.x_coor.text().replace(",","."))
        y_coor = float(self.fraction.y_coor.text().replace(",","."))
        self.load_dict["FractionX"] = x_coor
        self.load_dict["FractionY"] = y_coor
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].fraction_coor_map(x_coor, y_coor)
        self.frac_entry()
        self.kill_fraction()

    def loadCalibration(self):
        """Calculates Phi and M calibration values by using Calibration.py"""
        file = QFileDialog.getOpenFileName(self, 'Open file', str(self.load_dict['Cal Load']), 'Tiff (*.tif *.tiff)')
        if file[0] != '':
            bin_width = float(self.cal.bin_width.text().replace(",","."))
            freq = float(self.cal.Freq.text().replace(",","."))
            harmonic = float(self.cal.Harmonic.text().replace(",","."))
            tau_ref = float(self.cal.Tau.text().replace(",","."))
            self.load_dict['Cal Load'] = os.path.dirname(file[0])
            self.load_dict['Freq'] = freq
            self.load_dict['Bin Width'] = bin_width
            self.load_dict['Tau Ref'] = tau_ref
            self.load_dict['Harmonic'] = harmonic
            self.load_dict['Phi Cal'], self.load_dict['M Cal'] = \
                Calibration.get_calibration_parameters(file[0], bin_width, freq, harmonic, tau_ref)
            self.Phi_cal_box.setText("{:.4f}".format(self.load_dict['Phi Cal']))
            self.m_cal_box.setText("{:.4f}".format(self.load_dict['M Cal']))
            del self.cal

    def kill_cal(self):
        """closes the calibration window"""
        del self.cal

    def kill_fraction(self):
        """closes the fraction bound colormap window"""
        del self.fraction

    def change_frame(self, frame_selected):
        """Switches between the frames on the main UI, like home and the sliders. They're located in a stack, and
        they're just moved into position when selected."""
        x = self.current_frame.x()
        y = self.current_frame.y()
        width = self.current_frame.width()
        height = self.current_frame.height()
        self.current_frame.setGeometry(self.current_frame.size().width() + 200, 0, width, height)

        width = frame_selected.width()
        height = frame_selected.height()
        frame_selected.setGeometry(x, y, width, height)

        self.current_frame = frame_selected

    def move_block(self):
        """Moves the menu left and right when the "MENU" button is clicked, and updates the three bars into an image
        of a chevron"""
        self.animation = QPropertyAnimation(self.current_frame, b"geometry")
        self.animation.setDuration(500)
        y = self.current_frame.y()
        width = self.current_frame.width()
        height = self.current_frame.height()
        if self.menu_size > 0:
            self.animation.setEndValue(QRect(self.menu_x+self.menu_size,y,width,height))
            self.MoveFrame.setIcon(QIcon(dir_path + "/icons/chevron-left.svg"))
        else:
            self.animation.setEndValue(QRect(self.menu_x, y, width, height))
            self.MoveFrame.setIcon(QIcon(dir_path + "/icons/menu.svg"))
        self.menu_size = -1*self.menu_size
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def resizeEvent(self, event):
        """Runs when the window is resized."""
        windwWidth = event.size().width()
        windwHeight = event.size().height()
        frameSize = int((event.size().height()-63)/2.5)
        x_pos = self.current_frame.x()
        self.MainFrame.setGeometry(windwWidth + 55, 0, windwWidth - 55, frameSize)
        self.PictureFrame.setGeometry(windwWidth + 55, 0, windwWidth - 55, frameSize)
        self.GraphFrame.setGeometry(windwWidth + 55, 0, windwWidth - 55, frameSize)
        self.current_frame.setGeometry(x_pos, 33, windwWidth - 55, frameSize)
        self.FLUTELogo.setGeometry(windwWidth-136, 5, 111, 27)
        self.tableWidget.setGeometry(30, 43+frameSize, windwWidth-55, int(frameSize * 1.5))
        self.MenuButtonFrame.setGeometry(0, 30, 160, frameSize)
        self.BackgroundColor.resize(windwWidth+200, event.size().height()+200)
        self.load_dict['framex'] = windwWidth
        self.load_dict['framey'] = windwHeight

    def update_circle_range(self, *args, **kwargs):
        """Updates based on the values of the Modulation range slider"""
        self.M_min.setText("{:.2f}".format(args[0] / 100))
        self.M_max.setText("{:.2f}".format(args[1] / 100))
        self.M_entry()

    def update_angle_range(self, *args, **kwargs):
        """Updates based on the values of the Angle range slider"""
        self.Phi_min.setText(str(args[0]))
        self.Phi_max.setText(str(args[1]))
        self.phi_entry()

    def update_fraction_range(self, *args, **kwargs):
        """Updates based on the values of the Fraction range slider"""
        self.fractMin.setText("{:.2f}".format(args[0] / 100))
        self.fractMax.setText("{:.2f}".format(args[1] / 100))
        self.frac_min.setText(str(args[0]/100))
        self.frac_max.setText(str(args[1]/100))
        self.frac_entry()

    def fraction_set(self, *args, **kwargs):
        """Sets the fraction range for bulk saving"""
        min = float(self.fractMin.text().replace(",","."))
        max = float(self.fractMax.text().replace(",","."))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].update_fraction_range(min*100, max*100)

    def update_threshold(self):
        """Updates based on the values of the intensity threshold"""
        min_thresh = int(self.IntensityMin.text().replace(",","."))
        max_thresh = int(self.IntensityMax.text().replace(",","."))
        if max_thresh < min_thresh:
            max_thresh = min_thresh + 1
            self.IntensityMax.setText(str(max_thresh))
        self.ThreshMinLabel.setText(self.IntensityMin.text().replace(",","."))
        self.ThreshMaxLabel.setText(self.IntensityMax.text().replace(",","."))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].update_threshold(float(self.IntensityMin.text().replace(",",".")), float(self.IntensityMax.text().replace(",",".")))

    def clear_circles(self):
        """Removes the circles from the selected plots"""
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].clear_circles()

    def set_colormap(self, button_num):
        """sets the colourmap of the selected images"""
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].change_colormap(button_num)

    def reset_circles(self):
        """Resets all ranges of the sliders"""
        self.circleSlider.setHigh(120)
        self.circleSlider.setLow(0)
        self.angleSlider.setHigh(90)
        self.angleSlider.setLow(0)
        self.fractionSlider.setLow(0)
        self.fractionSlider.setHigh(120)
        self.update_circle_range(0,120)
        self.update_angle_range(0, 90)
        self.update_fraction_range(0, 120)

    def phi_entry(self):
        """Applies a phi angle threshold to selected images"""
        omega = 2 * np.pi * self.load_dict['Freq'] / 1000
        min_phi = float(self.Phi_min.text().replace(",","."))
        max_phi = float(self.Phi_max.text().replace(",","."))
        if max_phi <= min_phi:
            max_phi = min_phi + 1
            self.Phi_max.setText(str(max_phi))
        taumin = 1/omega*np.tan(np.deg2rad(min_phi))
        taumax = 1/omega*np.tan(np.radians(max_phi))
        self.TauPMinLabel.setText("TauP: " + "{:.2f}".format(taumin) + " ns")
        self.angleMinTauP.setText("{:.2f}".format(taumin) + " ns")
        if taumax < 15:
            self.TauPMaxLabel.setText("TauP: " + "{:.2f}".format(taumax) + " ns")
            self.angleMaxTauP.setText("{:.2f}".format(taumax) + " ns")
        else:
            self.TauPMaxLabel.setText("TauP: 15+ ns")
            self.angleMaxTauP.setText("ns: 15+")
        self.angleSlider.setHigh(int(float(self.Phi_max.text().replace(",","."))))
        self.angleSlider.setLow(int(float(self.Phi_min.text().replace(",","."))))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].update_angle_range(min_phi, max_phi)

    def M_entry(self):
        """Applies a modulation threshold to selected images"""
        omega = 2 * np.pi * self.load_dict['Freq'] / 1000
        min_m = float(self.M_min.text().replace(",","."))
        max_m = float(self.M_max.text().replace(",","."))
        if max_m <= min_m:
            max_m = min_m + 0.1
            self.M_max.setText(str(round(max_m, 2)))
        tauM_min = 1 / omega * np.sqrt(1 / np.power(min_m, 2) - 1)
        tauM_max = 1 / omega * np.sqrt(1 / np.power(max_m, 2) - 1)
        self.TauMMinLabel.setText("TauM: " + "{:.2f}".format(tauM_min) + " ns")
        self.TauMMaxLabel.setText("TauM: " + "{:.2f}".format(tauM_max) + " ns")
        self.circleMinTauM.setText("{:.2f}".format(tauM_min) + " ns")
        self.circleMaxTauM.setText("{:.2f}".format(tauM_max) + " ns")
        self.circleSlider.setHigh(int(float(self.M_max.text().replace(",","."))*100))
        self.circleSlider.setLow(int(float(self.M_min.text().replace(",","."))*100))
        self.M_min.setText("{:.2f}".format(min_m))
        self.M_max.setText("{:.2f}".format(max_m))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].update_circle_range(min_m*100, max_m*100)

    def frac_entry(self):
        """Opens entry box for fraction colourmapping"""
        min_frac = float(self.frac_min.text().replace(",","."))
        max_frac = float(self.frac_max.text().replace(",","."))
        self.fractionSlider.setHigh(int(max_frac * 100))
        self.fractionSlider.setLow(int(min_frac * 100))
        self.fractMin.setText("{:.2f}".format(min_frac))
        self.fractMax.setText("{:.2f}".format(max_frac))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].update_fraction_range(min_frac * 100, max_frac * 100)

    def cal_update(self):
        """updates the calibration values when the user changes them"""
        self.load_dict['Phi Cal'] = float(self.Phi_cal_box.text().replace(",","."))
        self.load_dict['M Cal'] = float(self.m_cal_box.text().replace(",","."))

    def applyFilter(self):
        """Applies convolutional median filters to selected images"""
        filters = int(float(self.Filters.text().replace(",",".")))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].convolution(filters)

    def applyAllFilters(self):
        """Applies all the filters available on the front panel"""
        self.applyFilter()
        self.update_threshold()
        self.phi_entry()
        self.M_entry()
        self.frac_entry()
        self.range_lines()

    def change_radius(self):
        """Changes the radius of the colour selection circles when the user clicks the plots"""
        radius = float(self.set_radius.text().replace(",","."))
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].set_radius(radius)

    def setActive(self):
        """Sets windows to be active based on the table widget. If the user clicks in the whitespace after all the
        available rows, then the last value is selected. This also needs to connect and disconnect the plot windows
        from drawing the circles if the window is not selected."""
        selection = self.tableWidget.selectionModel().selectedRows()
        if len(selection) == 0:
            self.tableWidget.selectRow(len(self.image_arr) - 1)
        selection = self.tableWidget.selectionModel().selectedRows()
        selected_rows = [i.row() for i in selection]
        for i in range(len(self.image_arr)):
            if i in selected_rows:
                self.image_arr[i].set_active(True)
                self.image_arr[i].binding_id = \
                    self.image_arr[i].graph_window.Plot.canvas.mpl_connect('button_press_event', self.update_circle)
            else:
                self.image_arr[i].set_active(False)
                self.image_arr[i].graph_window.Plot.canvas.mpl_disconnect(self.image_arr[i].binding_id)

    def save_data_popup(self):
        """Opens the save data window and connects buttons"""
        self.save_window = DataWindows.SaveWindow()
        self.save_window.AllData.clicked.connect(lambda: self.save_data('all'))
        self.save_window.CurrentData.clicked.connect(lambda: self.save_data('current'))
        self.save_window.show()

    def save_data(self, type):
        """Opens a save file dialog and saves the images and parameters"""
        self.kill_save_window()
        file = QFileDialog.getExistingDirectory(self, directory = self.load_dict['save_Dir'])
        self.save_type = type
        if file != '':
            self.save_selected_data(file)

    def save_selected_data(self, file_path):
        """Saves all selected data in the table widget to file_path"""
        self.load_dict['save_Dir'] = file_path
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].save_data(file_path, self.save_type)

    def kill_save_window(self):
        """closes the save selection window"""
        del self.save_window
                
    def no_update(self, event):
        """Do nothing. Used for when the user clicks an inactive plot window"""
        pass

    def CloseWindows(self):
        """Closes all the windows the user has selected in the table widget at once. Used to clean up the workspace"""
        self.close = DataWindows.CloseWindows()
        self.close.show()
        self.close.CancelClose.clicked.connect(self.kill_close)
        self.close.CloseFiles.clicked.connect(self.close_windows)

    def kill_close(self):
        """closes the close windows dialog window"""
        del self.close

    def close_windows(self):
        """closes all the widnows the user has selected on the table widget, to clean up the workspace"""
        del self.close
        selection = self.tableWidget.selectionModel().selectedRows()
        for i in selection:
            self.image_arr[i.row()].kill()

    def closeEvent(self, event):
        """Closes all open windows when the main window is closed"""
        for window in self.image_arr:
            window.kill()
            del window
        with open('saved_dict.pkl', 'wb') as f:
            pickle.dump(self.load_dict, f)
        sys.exit()

# Executes the MainWindow
if __name__ == "__main__":
    if platform.system() == "Windows":
        make_dpi_aware()
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    myappid = 'LOB.FLUTE.1.0'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QIcon((resource_path(dir_path + "/icons/logo.ico"))))
    window = MainWindow()
    window.show()
    app.exec_()
