# Holds the classes to display the image, and to generate the matplotlib plot of the data, including the colormaps
# and the ranges specified by the user

#imports
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt
import numpy as np
import cv2
import matplotlib.patches as patches
import matplotlib
matplotlib.use('Qt5Agg')
import os
from matplotlib.image import NonUniformImage
import MplWidget

dir_path = os.path.dirname(os.path.realpath(__file__))

class Picture(QtWidgets.QMainWindow):
	"""Creates the picture window, and displays the images supplied by ImageHandler"""
	def __init__(self, name):
		super(Picture, self).__init__()

		height, width, channel = 300, 300, 3
		bytesPerLine = 3 * width

		self.widget = QLabel("HelloWorld")
		self.widget.setScaledContents(True)
		font = self.widget.font()
		font.setPointSize(30)
		self.widget.setFont(font)
		self.widget.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

		self.setCentralWidget(self.widget)
		self.name = name

		self.dead = False

	def set_image(self, im):
		"""Displays the image im"""
		im = cv2.resize(im, (300, 300))
		qImg = QImage(im.data, 300,300, QImage.Format_RGB888)
		self.widget.setPixmap(QPixmap(qImg))

	def closeEvent(self, event):
		"""Ran when the window is closed"""
		self.dead = True

	def set_window_number(self, num):
		"""Sets the title of the window to match the number in the table on the front panel"""
		self.setWindowTitle(str(num) +': ' + self.name)


class Calibration(QtWidgets.QMainWindow):
	"""Opens the calibration entry window to type in the lifetime"""
	def __init__(self):
		super(Calibration, self).__init__()
		uic.loadUi(dir_path + "/ui files/CalibrationWindow.ui", self)


class CloseWindows(QtWidgets.QMainWindow):
	"""Opens the dialog to ask if the user really wants to close the windows"""
	def __init__(self):
		super(CloseWindows, self).__init__()
		uic.loadUi(dir_path + "/ui files/CloseWindow.ui", self)


class Fraction(QtWidgets.QMainWindow):
	"""Opens the fraction bound entry window"""
	def __init__(self):
		super(Fraction, self).__init__()
		uic.loadUi(dir_path + "/ui files/BoundEntry.ui", self)


class SaveWindow(QtWidgets.QMainWindow):
	"""Opens the window to enter what type of data to save. All or just current"""
	def __init__(self):
		super(SaveWindow, self).__init__()
		uic.loadUi(dir_path + "/ui files/SaveData.ui", self)


class Graph(QtWidgets.QMainWindow):
	"""Displays the MplWidget plot based on the thresholding parameters that the user enters"""
	def __init__(self, name, MHz):
		super(Graph, self).__init__()

		self.ui = uic.loadUi(dir_path + "/ui files/Graph.ui", self)

		x = np.linspace(0, 1, 1000)
		y = np.sqrt(0.5 * 0.5 - (x - 0.5) * (x - 0.5))
		self.Plot.canvas.ax.set_xlim([0, 1])
		self.Plot.canvas.ax.set_ylim([0, 0.6])
		self.Plot.canvas.ax.plot(x, y, 'r')
		self.Plot.canvas.ax.set_xlabel('g', fontsize=12, weight='bold')
		self.Plot.canvas.ax.set_ylabel('s', fontsize=12, weight='bold')

		self.MHz = '{0:.0f}'.format(MHz)

		# load the range lines horizontally and vertically
		y = np.tan((np.radians(0)) * x - 0.001)
		self.min_line, = self.Plot.canvas.ax.plot(x,y)

		y = np.tan(np.radians(90)) * x
		self.max_line, = self.Plot.canvas.ax.plot(x, y)

		self.min_circle, = self.Plot.canvas.ax.plot(x, y)
		self.max_circle, = self.Plot.canvas.ax.plot(x, y)

		self.circle_coors = np.full((4, 2),-3.0)
		self.circle_radius = [0.05, 0.05, 0.05, 0.05]

		self.circler = patches.Circle((-2, -2), 0.05, ec='r', alpha=0.7, lw=2.5)
		self.circleg = patches.Circle((-2, -2), 0.05, ec='g', alpha=0.7, lw=2.5)
		self.circleb = patches.Circle((-2, -2), 0.05, ec='b', alpha=0.7, lw=2.5)
		self.circley = patches.Circle((-2, -2), 0.05, ec='y', alpha=0.7, lw=2.5)

		self.Plot.canvas.ax.add_patch(self.circler)
		self.Plot.canvas.ax.add_patch(self.circleg)
		self.Plot.canvas.ax.add_patch(self.circleb)
		self.Plot.canvas.ax.add_patch(self.circley)

		self.circle_fraction_min = patches.Circle((0, 0), 0, ec='r', fill=0, lw=1.5)
		self.circle_fraction_max = patches.Circle((0, 0), 1.2, ec='r', fill=0, lw=1.5)

		self.Plot.canvas.ax.add_patch(self.circle_fraction_min)
		self.Plot.canvas.ax.add_patch(self.circle_fraction_max)

		self.name = name

		self.angle_min_val = 0
		self.angle_max_val = 90
		self.circle_min_val = 0
		self.circle_max_val = 120
		self.fraction_min = 0
		self.fraction_max = 1.2
		self.line_alpha = 1.0

		self.image_min_ang, self.image_max_ang = 0, 90
		self.image_min_M, self.image_max_M = 0, 120

		self.color_map = 0 #0=densitymap, 1=TauM, 2=TauP, 3=densitymap, 4=fractionBound

		self.cmap = matplotlib.cm.jet.copy()
		self.cmap_r = matplotlib.cm.jet_r.copy()
		self.cmap.set_bad('k', alpha=0)
		self.cmap_noir = matplotlib.cm.Greys.copy()

		self.x_fraction = 0
		self.y_fraction = 0

		self.dead = False

	def resizeEvent(self, event):
		self.Plot.setGeometry(0, 0, event.size().width(), event.size().height())

	def plot_data(self, x_data, y_data):
		"""Plots the xy data given by image handler, and colors based on the thresholds and colormap selected by the
		user"""
		# Placing the data into a histogram with reasonably sized binning helps speed up the plotting significantly
		H, xedges, yedges = np.histogram2d(x_data, y_data, bins=150, range=[[0, 1], [0, 0.6]])
		H = H.T
		xcenters = (xedges[:-1] + xedges[1:]) / 2
		ycenters = (yedges[:-1] + yedges[1:]) / 2
		x = np.tile(xcenters, (150,1))
		y = np.tile(ycenters, (150,1)).T
		# pre calculate distance D, fraction bound F, and angle A maps for the data
		D = np.sqrt(x**2+y**2)
		F = np.sqrt((x-self.x_fraction)**2+(y-self.y_fraction)**2)
		A = y/x
		min = np.tan(np.deg2rad(self.angle_min_val))
		max = np.tan(np.deg2rad(self.angle_max_val))
		# Convert the plot to an image, which makes it faster to plot than the raw data
		im = NonUniformImage(self.Plot.canvas.ax, interpolation='bilinear', cmap=self.cmap)
		im2 = NonUniformImage(self.Plot.canvas.ax, interpolation='bilinear', cmap=self.cmap_noir)
		im.set_data(xcenters, ycenters, A)
		# These if statements color the top image based on the thresholds, and then sets areas outside the thresholding
		# to be black.
		if self.color_map == 0:
			H = np.ma.masked_where(H < 0.005, H)
			im.set_data(xcenters, ycenters, H)
			H[H != 0] = 1
			im2.set_data(xcenters, ycenters, H)
		elif self.color_map == 1:
			im = NonUniformImage(self.Plot.canvas.ax, interpolation='bilinear', cmap=self.cmap_r)
			D = np.ma.masked_where((D < self.circle_min_val / 100) | (D > self.circle_max_val / 100) | (H < 0.01) |
								   (A < min) | (A > max) | (F<self.fraction_min) | (F>self.fraction_max),D)
			H[H != 0] = 1
			if not False in D.mask:
				D.mask[0, 0] = False
			im.set_data(xcenters, ycenters, D)
			im.set_clim(self.circle_min_val / 100, self.circle_max_val / 100)
			im2.set_data(xcenters, ycenters, H)
		elif self.color_map == 2:
			A[(A > self.image_max_ang) & (A < max)] = self.image_max_ang
			A[(A < self.image_min_ang) & (A > min)] = self.image_min_ang
			A = np.ma.masked_where((D < self.circle_min_val / 100) | (D > self.circle_max_val / 100) | (H < 0.01) |
								   (A < min) | (A > max) | (F<self.fraction_min) | (F>self.fraction_max),A)
			if not False in A.mask:
				A.mask[0, 0] = False
			im.set_data(xcenters, ycenters, A)
			im.set_clim(min, max)
			H[H != 0] = 1
			im2.set_data(xcenters, ycenters, H)
		elif self.color_map == 4:
			F = np.ma.masked_where((D < self.circle_min_val / 100) | (D > self.circle_max_val / 100) | (H < 0.01) |
								   (A < min) | (A > max) | (F<self.fraction_min) | (F>self.fraction_max),F)
			H[H != 0] = 1
			if not False in F.mask:
				F.mask[0, 0] = False
			im.set_data(xcenters, ycenters, F)
			im.set_clim(self.fraction_min, self.fraction_max)
			im2.set_data(xcenters, ycenters, H)
		for item in self.Plot.canvas.ax.get_images():
			item.remove()
		# Plot one image on top which has all the colours, and one image on the bottom which is just black to show the
		# points which are outside of the thresholding
		self.Plot.canvas.ax.add_image(im2)
		self.Plot.canvas.ax.add_image(im)
		if len(self.MHz) <= 2:
			self.Plot.canvas.ax.text(0.8, 0.55, self.MHz + " MHz", fontsize  = 12)
		else:
			self.Plot.canvas.ax.text(0.75, 0.55, self.MHz + " MHz", fontsize=12)
		# list = self.Plot.canvas.ax.get_images()


	def set_circle(self, selection):
		"""Changes the colour of the circle seleted for when the user clicks the plot based on the value in the
		enumerated dropdown box on the front panel"""
		self.circleSelect = selection

	def clear_circles(self):
		"""Sends all the circles to far outside the plot coordinates"""
		self.circle_coors[:] = -3.0
		self.draw_circles()

	def update_circle(self, event):
		"""Moves the selected circles"""
		self.circle_coors[self.circleSelect][0] = event.xdata
		self.circle_coors[self.circleSelect][1] = event.ydata
		self.draw_circles()

	def draw_circles(self):
		"""Draws the circles. Using patches as opposed to plotting them is far more efficient, otherwise the program
		hangs for a while"""
		self.circler.remove()
		self.circler = patches.Circle((self.circle_coors[0][0], self.circle_coors[0][1]), self.circle_radius[0],
									  ec='r', fill=0, alpha=0.7, lw=2.5)
		self.Plot.canvas.ax.add_patch(self.circler)

		self.circleg.remove()
		self.circleg = patches.Circle((self.circle_coors[1][0], self.circle_coors[1][1]), self.circle_radius[1],
									  ec='g', fill=0, alpha=0.7, lw=2.5)
		self.Plot.canvas.ax.add_patch(self.circleg)

		self.circleb.remove()
		self.circleb = patches.Circle((self.circle_coors[2][0], self.circle_coors[2][1]), self.circle_radius[2],
									  ec='b', fill=0, alpha=0.7, lw=2.5)
		self.Plot.canvas.ax.add_patch(self.circleb)

		self.circley.remove()
		self.circley = patches.Circle((self.circle_coors[3][0], self.circle_coors[3][1]), self.circle_radius[3],
									  ec='y', fill=0, alpha=0.7, lw=2.5)
		self.Plot.canvas.ax.add_patch(self.circley)

		self.Plot.canvas.draw()

	def update_fraction_range(self, min, max, *args, **kwargs):
		"""Draws the circles for fraction range. Need to clear plot and then redraw it. This is why it's far more
		efficient to work with images rather than the raw histogram data"""
		self.fraction_min = min
		self.fraction_max = max
		self.circle_fraction_min.remove()
		self.circle_fraction_max.remove()
		self.circle_fraction_min = patches.Circle((self.x_fraction, self.y_fraction), min, ec='b', fill=0, lw=1.5, alpha = self.line_alpha)
		self.circle_fraction_max = patches.Circle((self.x_fraction, self.y_fraction), max, ec='b', fill=0, lw=1.5, alpha = self.line_alpha)
		self.Plot.canvas.ax.add_patch(self.circle_fraction_min)
		self.Plot.canvas.ax.add_patch(self.circle_fraction_max)
		self.Plot.canvas.draw()

	def update_angle_range(self, min, max, *args, **kwargs):
		"""Draws the lines for angle range. Need to clear plot and then redraw it. This is why it's far more
		efficient to work with images rather than the raw histogram data"""
		self.min_line.remove()
		self.max_line.remove()
		x = np.linspace(0,2,3)
		y = np.tan((np.deg2rad(min)))*x
		if y[-1] == 0:
			y = [-1, -1, -1]

		self.min_line, = self.Plot.canvas.ax.plot(x, y, color='r', alpha = self.line_alpha)

		y = np.tan(np.radians(max))*x
		self.max_line, = self.Plot.canvas.ax.plot(x, y, color = 'r', alpha = self.line_alpha)

		self.angle_min_val = min
		self.angle_max_val = max

	def update_circle_range(self, min, max, *args, **kwargs):
		"""Draws the circles for modulation range. Need to clear plot and then redraw it. This is why it's far more
		efficient to work with images rather than the raw histogram data"""
		self.min_circle.remove()
		self.max_circle.remove()

		x1 = np.linspace(0, min/100, 100)
		y1 = np.sqrt((min/100)**2 - x1**2)
		self.min_circle, = self.Plot.canvas.ax.plot(x1, y1, color='r', alpha = self.line_alpha)

		x2 = np.linspace(0, max/100, 100)
		y2 = np.sqrt((max/100)**2 - x2**2)
		self.max_circle, = self.Plot.canvas.ax.plot(x2, y2, color='r', alpha = self.line_alpha)

		self.circle_min_val = min
		self.circle_max_val = max

	def change_circle_radius(self, radius):
		"""Makes the click circles of radius = radius"""
		self.circle_radius[self.circleSelect] = radius
		self.draw_circles()

	def closeEvent(self, event):
		"""Ran when the window is closed"""
		self.dead = True

	def update_data(self, x, y, col_map = 0):
		"""plots new data, and adds the thresholding lines and circles to a new plot"""
		self.plot_data(x.flatten(),y.flatten())
		self.update_angle_range(self.angle_min_val, self.angle_max_val)
		self.update_circle_range(self.circle_min_val, self.circle_max_val)
		self.draw_circles()

	def set_window_number(self, num):
		"""Sets the title of the window"""
		self.setWindowTitle(str(num) +': ' + self.name)

	def set_colormap(self, val):
		"""updates the colormap value"""
		self.color_map = val

	def set_image_props(self, min_ang, max_ang, min_m, max_m):
		"""Changes the thresholding parameters for angle and modulation"""
		self.image_min_ang = min_ang
		self.image_max_ang = max_ang
		self.image_min_M = min_m
		self.image_max_M = max_m

	def set_lifetime_points(self, *args):
		"""Adds the lifetime values to the universal circle"""
		lifetime_x = args[0][0]
		lifetime_y = args[0][1]
		lifetimes = [0.5, 1, 2, 3, 4, 8]
		self.Plot.canvas.ax.scatter(lifetime_x, lifetime_y, color='r', s=10)
		for i in range(6):
			self.Plot.canvas.ax.text(lifetime_x[i]-0.05, lifetime_y[i]+0.03, str(lifetimes[i]) + " ns", color='r', fontsize=9)

	def set_fraction(self, x, y):
		"""Changes the thresholding parameters for the fraction bound circles"""
		self.x_fraction = x
		self.y_fraction = y

	def save_fig(self, file):
		"""Saves a picture of the plot in file path"""
		self.Plot.canvas.save_fig(file)

	def set_alpha(self, value):
		self.line_alpha = value
		self.update_circle_range(self.circle_min_val, self.circle_max_val)
		self.update_angle_range(self.angle_min_val, self.angle_max_val)
		self.update_fraction_range(self.fraction_min, self.fraction_max)


