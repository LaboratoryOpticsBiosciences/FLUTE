# Handles all the calculations for the data, such as taking the fft and applying the convolutional filters


# imports
from skimage import io
import DataWindows
import numpy as np
from PIL import Image
import os
from matplotlib import cm
from scipy import signal
import tifffile

np.seterr(divide='ignore', invalid='ignore')


class ImageHandler:
	"""Handles the calculations for the images, taken in as tiff stacks located at filename"""

	def __init__(self, filename, phi_cal=0, m_cal=1, bin_width=0.2208, freq=80, harmonic=1):
		im = io.imread(filename)
		self.name = os.path.splitext(os.path.basename(filename))[0]
		self.original_image = np.sum(im, axis=0)
		self.max = np.max(self.original_image)
		self.min = np.min(self.original_image)
		self.compress_image(self.original_image)

		self.phi_cal = float(phi_cal)
		self.m_cal = float(m_cal)
		self.bin_width = float(bin_width)
		self.freq = float(freq)
		self.harmonic = float(harmonic)

		# Record the fft coordinates as g and s
		self.g, self.s = self.perform_fft(im)
		self.xcoor_map = self.g.reshape(self.original_image.shape)
		self.x_adjusted = self.xcoor_map.copy()

		self.ycoor_map = self.s.reshape(self.original_image.shape)
		self.y_adjusted = self.ycoor_map.copy()

		self.graph_window = DataWindows.Graph(self.name)
		self.graph_window.set_lifetime_points(self.get_phasor_lifetime_coordinates())
		self.graph_window.show()
		self.graph_window.plot_data(self.g, self.s)

		self.graph_window.Plot.canvas.mpl_connect('button_press_event', self.update_circle)

		self.plot_angle_mask = np.zeros(self.original_image.shape, dtype=bool)
		self.plot_circle_mask = np.zeros(self.original_image.shape, dtype=bool)
		self.plot_fraction_mask = np.zeros(self.original_image.shape, dtype=bool)
		self.intensity_mask = np.zeros(self.original_image.shape, dtype=bool)

		self.angle_arr = self.ycoor_map / self.xcoor_map
		self.distance_arr = np.sqrt(self.ycoor_map ** 2 + self.xcoor_map ** 2)
		self.fraction_arr = self.distance_arr
		self.color_map = np.zeros((im.shape[1], im.shape[2], 4), dtype=bool)

		self.selected_circle = 0
		self.color_map_select = 0
		self.min_thresh = 0
		self.max_thresh = 1000000
		self.x_fraction = 0
		self.y_fraction = 0
		self.num_filter = 0
		self.active = True
		self.binding_id = None

		self.image_min_ang, self.image_max_ang = 0, 90
		self.applied_min_ang, self.applied_max_ang = 0, 90
		self.image_min_M, self.image_max_M = 0, 120
		self.applied_min_M, self.applied_max_M = 0, 120
		self.fraction_min, self.fraction_max = 0, 1

		self.image_window = DataWindows.Picture(self.name)
		self.image_window.show()
		self.image_window.set_image(self.displayImage)
		self.change_colormap(0)

	def colormaps(self, mask):
		"""applies the colormap selected to the image"""
		if self.color_map_select == 0:
			im = self.original_image.copy()
			if len(im[~mask]) != 0:
				im = ((im - np.min(im[~mask])) * (1 / (np.max(im[~mask]) - np.min(im[~mask])) * 255))
			im = im.astype('uint8')
			im[mask] = 0
			im = np.stack((im,) * 3, axis=-1)
			self.displayImage = im

		elif self.color_map_select == 1:
			viridis = cm.get_cmap('jet_r', 20)
			arr = self.distance_arr.copy()
			arr[arr < 0] = 0
			arr[mask] = 0
			if len(arr[~mask]) != 0:
				self.image_min_M = np.min(arr[~mask])
				self.image_max_M = np.max(arr[~mask])
				arr = (arr - self.applied_min_M/100) * (1 / (self.applied_max_M/100 - self.applied_min_M/100))
			else:
				self.image_min_M = np.min(arr)
				self.image_max_M = np.max(arr)
			col_map = viridis(arr)[..., :3]
			self.displayImage[..., 0] = np.asarray(col_map[..., 0] * 255).astype(int)
			self.displayImage[..., 1] = np.asarray(col_map[..., 1] * 255).astype(int)
			self.displayImage[..., 2] = np.asarray(col_map[..., 2] * 255).astype(int)
			self.displayImage[mask] = [0, 0, 0]

		elif self.color_map_select == 2:
			viridis = cm.get_cmap('jet', 20)
			arr = self.angle_arr.copy()
			arr[arr < 0] = 0
			np.nan_to_num(arr, copy=False)
			if len(arr[~mask]) != 0:
				self.image_min_ang =  np.tan(np.deg2rad(self.applied_min_ang))
				self.image_max_ang = np.tan(np.deg2rad(self.applied_max_ang))
				arr = (arr - self.image_min_ang) * (1 / (self.image_max_ang - self.image_min_ang))
			else:
				self.image_min_ang = np.min(arr)
				self.image_max_ang = np.max(arr)
			arr[mask] = 0
			col_map = viridis(arr)[..., :3]
			self.displayImage[..., 0] = np.asarray(col_map[..., 0] * 255).astype(int)
			self.displayImage[..., 1] = np.asarray(col_map[..., 1] * 255).astype(int)
			self.displayImage[..., 2] = np.asarray(col_map[..., 2] * 255).astype(int)
			self.displayImage[mask] = [0, 0, 0]

		elif self.color_map_select == 3:
			viridis = cm.get_cmap('jet', 20)
			im = self.original_image.copy()
			if len(im[~mask]) != 0:
				im = ((im - np.min(im[~mask])) * (1 / (np.max(im[~mask]) - np.min(im[~mask]))))
			im[mask] = 0
			col_map = viridis(im)[..., :3]
			self.displayImage[..., 0] = np.asarray(col_map[..., 0] * 255).astype(int)
			self.displayImage[..., 1] = np.asarray(col_map[..., 1] * 255).astype(int)
			self.displayImage[..., 2] = np.asarray(col_map[..., 2] * 255).astype(int)
			self.displayImage[mask] = [0, 0, 0]

		elif self.color_map_select == 4:
			viridis = cm.get_cmap('jet', 20)
			arr = self.fraction_arr.copy()
			arr[arr < 0] = 0
			if len(arr[~mask]) != 0:
				self.fraction_min = np.min(arr[~mask])
				self.fraction_max = np.max(arr[~mask])
				arr = (arr - np.min(arr[~mask])) * (1 / (np.max(arr[~mask]) - np.min(arr[~mask])))
			else:
				self.fraction_min = np.min(arr)
				self.fraction_max = np.max(arr)
			arr[mask] = 0
			col_map = viridis(arr)[..., :3]
			self.displayImage[..., 0] = np.asarray(col_map[..., 0] * 255).astype(int)
			self.displayImage[..., 1] = np.asarray(col_map[..., 1] * 255).astype(int)
			self.displayImage[..., 2] = np.asarray(col_map[..., 2] * 255).astype(int)
			self.displayImage[mask] = [0, 0, 0]

	def compress_image(self, im):
		"""Converts the image to be normalized and in the proper format to be displayed"""
		im = ((im - self.min) * (1 / (self.max - self.min) * 255)).astype('uint8')
		im = np.stack((im,) * 3, axis=-1)
		self.displayImage = im

	def update_circle(self, event=0):
		"""Colors the image based on the coordinates of the circles where the user clicks on the plot"""
		if self.active == True:
			if event != 0:
				self.graph_window.update_circle(event)
			circle_coor = self.graph_window.circle_coors
			radii = self.graph_window.circle_radius
			self.color_map[...] = False
			self.color_map[..., 0][
				(circle_coor[0, 0] - self.xcoor_map) ** 2 + (circle_coor[0, 1] - self.ycoor_map) ** 2 < radii[
					0] ** 2] = True
			self.color_map[..., 1][
				(circle_coor[1, 0] - self.xcoor_map) ** 2 + (circle_coor[1, 1] - self.ycoor_map) ** 2 < radii[
					1] ** 2] = True
			self.color_map[..., 2][
				(circle_coor[2, 0] - self.xcoor_map) ** 2 + (circle_coor[2, 1] - self.ycoor_map) ** 2 < radii[
					2] ** 2] = True
			self.color_map[..., 3][
				(circle_coor[3, 0] - self.xcoor_map) ** 2 + (circle_coor[3, 1] - self.ycoor_map) ** 2 < radii[
					3] ** 2] = True
			self.apply_masks()

	def update_circle_range(self, min, max):
		"""Updates thresholding and colormaps based on the TauM modulation thresholds"""
		self.graph_window.update_circle_range(min, max)
		self.applied_min_M, self.applied_max_M = min, max
		self.plot_circle_mask = np.logical_or(self.distance_arr > (max / 100), self.distance_arr < (min / 100))
		self.apply_masks()
		thresh = np.logical_or(self.original_image < self.min_thresh, self.original_image > self.max_thresh)
		self.graph_window.set_image_props(self.image_min_ang, self.image_max_ang, self.image_min_M, self.image_max_M)
		self.graph_window.update_data(self.x_adjusted[~thresh], self.y_adjusted[~thresh])

	def update_fraction_range(self, min, max):
		"""Updates thresholding and colormaps based on the fraction bound thresholds"""
		self.fraction_min = min / 100
		self.fraction_max = max / 100
		self.graph_window.update_fraction_range(self.fraction_min, self.fraction_max)
		self.plot_fraction_mask = np.logical_or(self.fraction_arr > max / 100, self.fraction_arr < min / 100)
		self.apply_masks()
		thresh = np.logical_or(self.original_image < self.min_thresh, self.original_image > self.max_thresh)
		self.graph_window.update_data(self.x_adjusted[~thresh], self.y_adjusted[~thresh])

	def update_angle_range(self, min, max):
		"""Updates thresholding and colormaps based on the TauP angle thresholds"""
		self.graph_window.update_angle_range(min, max)
		self.applied_min_ang, self.applied_max_ang = min, max
		min = np.tan(np.deg2rad(min))
		max = np.tan(np.deg2rad(max))
		self.plot_angle_mask = np.logical_or(self.angle_arr > max, self.angle_arr < min)
		self.apply_masks()
		self.graph_window.set_image_props(self.image_min_ang, self.image_max_ang, self.image_min_M, self.image_max_M)
		thresh = np.logical_or(self.original_image < self.min_thresh, self.original_image > self.max_thresh)
		self.graph_window.update_data(self.x_adjusted[~thresh], self.y_adjusted[~thresh])

	def apply_masks(self):
		"""Sets parts of the image outside the thresholds on the plot to black"""
		mask = self.plot_angle_mask | self.plot_circle_mask | self.intensity_mask | self.plot_fraction_mask
		mask = np.logical_or(mask, self.x_adjusted < 0)
		self.colormaps(mask)
		self.displayImage[..., :][self.color_map[..., 0]] = [255, 0, 0]
		self.displayImage[..., :][self.color_map[..., 1]] = [0, 255, 0]
		self.displayImage[..., :][self.color_map[..., 2]] = [0, 0, 255]
		self.displayImage[..., :][self.color_map[..., 3]] = [255, 255, 0]
		self.displayImage[mask] = [0, 0, 0]
		self.image_window.set_image(self.displayImage)
		self.graph_window.set_image_props(self.image_min_ang, self.image_max_ang, self.image_min_M, self.image_max_M)
		return mask

	def show_lines(self, show):
		self.graph_window.set_alpha(int(show))

	def update_threshold(self, min, max):
		"""Creates an intensity mask based on the threshold by the user through min and max"""
		self.min_thresh = min
		self.max_thresh = max
		intensity_mask = np.logical_or(self.original_image < min, self.original_image > max)
		self.graph_window.update_data(self.x_adjusted[~intensity_mask], self.y_adjusted[~intensity_mask])
		self.intensity_mask = np.logical_or(self.original_image < min, self.original_image > max)
		self.apply_masks()

	def set_circle(self, selection):
		"""Selects which color circle is currently active"""
		self.selected_circle = selection
		self.graph_window.set_circle(selection)

	def clear_circles(self):
		"""Removes the circles from the plot and the colormap"""
		self.color_map[...] = False
		self.graph_window.clear_circles()
		self.apply_masks()

	def get_image_params(self):
		"""Returns image parameters"""
		return self.name, self.original_image.shape

	def perform_fft(self, image):
		"""Performs fft on the image data to get the g and s coordinates. see https://doi.org/10.1073/pnas.1108161108"""
		image = np.moveaxis(image, 0, 2)
		bins = image.shape[2]
		t_arr = np.linspace(self.bin_width / 2, self.bin_width * (bins - 1 / 2), bins)

		integral = np.sum(image, axis=2).astype(float)
		integral[integral == 0] = 0.00001
		g = np.sum(image[:, ...] * np.cos(2 * np.pi * self.freq / 1000 * self.harmonic * t_arr[:]), axis=2) / integral
		s = np.sum(image[:, ...] * np.sin(2 * np.pi * self.freq / 1000 * self.harmonic * t_arr[:]), axis=2) / integral

		R = np.array(((np.cos(self.phi_cal), -np.sin(self.phi_cal)), (np.sin(self.phi_cal), np.cos(self.phi_cal))))
		mask = np.ones(image.shape[:2]).astype(bool)
		arr = R.dot([g[mask], s[mask]]) * self.m_cal

		g_coor = arr[0].flatten()
		s_coor = arr[1].flatten()
		return g_coor, s_coor

	def dead(self):
		"""Detects if one window is dead, and then kills the other one so that they both close."""
		if self.graph_window.dead:
			self.image_window.close()
		if self.image_window.dead:
			self.graph_window.close()
		return np.logical_or(self.graph_window.dead, self.image_window.dead)

	def kill(self):
		"""Closes the other window if it's dead"""
		self.image_window.close()
		self.graph_window.close()

	def change_colormap(self, val):
		"""Changes the colormap to the value val. 0=densitymap, 1=TauM, 2=TauP, 3=densitymap, 4=fractionBound"""
		self.graph_window.set_colormap(val)
		if val == 0 and self.color_map_select == 0:
			self.color_map_select = 3
		elif val == 0 and self.color_map_select != 3:
			self.color_map_select = 3
		else:
			self.color_map_select = val
		self.apply_masks()
		thresh = np.logical_or(self.original_image < self.min_thresh, self.original_image > self.max_thresh)
		self.graph_window.update_data(self.x_adjusted[~thresh], self.y_adjusted[~thresh])

	def set_radius(self, size):
		"""Changes the size of the selection circles"""
		self.graph_window.change_circle_radius(size)
		self.update_circle(0)

	def set_active(self, state):
		"""Changes the state of the data, which controls if the red circles should be drawn or not when the window is
		clicked"""
		self.active = state

	def fraction_lifetime_map(self, lifetime):
		"""Creates the mapping of the coordinates in the plot based on their distance from the lifetime of the
		fluorophore entered by the user. For example, 0.4ns for NADH."""
		self.x_fraction = 1 / (1 + np.power(2 * np.pi * self.freq / 1000 * lifetime, 2))
		self.y_fraction = 2 * np.pi * self.freq / 1000 * lifetime / (
				1 + np.power(2 * np.pi * self.freq / 1000 * lifetime, 2))
		self.fraction_arr = np.sqrt((self.ycoor_map - self.y_fraction) ** 2 + (self.xcoor_map - self.x_fraction) ** 2)
		self.graph_window.set_fraction(self.x_fraction, self.y_fraction)
		self.change_colormap(4)

	def fraction_coor_map(self, x_coor, y_coor):
		"""Creates the mapping of the coordinates in the plot based on their distance from the lifetime of the
		fluorophore entered by the user. For example, 0.4ns for NADH."""
		self.x_fraction = x_coor
		self.y_fraction = y_coor
		self.fraction_arr = np.sqrt((self.ycoor_map - self.y_fraction) ** 2 + (self.xcoor_map - self.x_fraction) ** 2)
		self.graph_window.set_fraction(self.x_fraction, self.y_fraction)
		self.change_colormap(4)

	def get_phasor_lifetime_coordinates(self):
		"""Gets the coordinates for the points along the universal circles, which are used a reference when looking
		at the plots"""
		points = np.asarray([0.5, 1, 2, 3, 4, 8])
		x_coors = 1 / (1 + np.power(2 * np.pi * self.freq / 1000 * points, 2))
		y_coors = 2 * np.pi * self.freq / 1000 * points / (1 + np.power(2 * np.pi * self.freq / 1000 * points, 2))
		return x_coors, y_coors

	def convolution(self, num_filter):
		"""Applies a 3x3 convolutional median filter to the graph data num_filter times. See:
		https://doi.org/10.1038/s41596-018-0026-5"""
		self.num_filter = num_filter
		self.x_adjusted = self.g.copy()
		self.x_adjusted = self.x_adjusted.reshape(self.original_image.shape)
		self.y_adjusted = self.s.copy()
		self.y_adjusted = self.y_adjusted.reshape(self.original_image.shape)
		for i in range(num_filter):
			self.x_adjusted = signal.medfilt(self.x_adjusted)
			self.y_adjusted = signal.medfilt(self.y_adjusted)
		self.x_adjusted[self.x_adjusted == 0] = -0.1
		thresh = np.logical_or(self.original_image < self.min_thresh, self.original_image > self.max_thresh)
		self.graph_window.update_data(self.x_adjusted[~thresh], self.y_adjusted[~thresh])

		self.angle_arr = self.y_adjusted / self.x_adjusted
		self.distance_arr = np.sqrt(self.y_adjusted ** 2 + self.x_adjusted ** 2)
		self.fraction_arr = np.sqrt((self.ycoor_map - self.y_fraction) ** 2 + (self.xcoor_map - self.x_fraction) ** 2)

	def set_data_num(self, num):
		"""Updates the titles of the windows to keep track of the window number"""
		self.image_window.set_window_number(num)
		self.graph_window.set_window_number(num)

	def save_data(self, file, save_type):
		"""Saves all the images of the various colormaps, the g and s coordinates, and a file that contains all the
		parameters used to create the data."""
		colormap = self.color_map_select
		self.color_map_select = 3
		self.change_colormap(0)
		mask = self.apply_masks()
		image = Image.fromarray(self.displayImage)
		if save_type == 'all' or (save_type == 'current' and colormap == 0):
			image.save(file + '/' + self.name + '_image_Intensity.tif')
			self.graph_window.save_fig(file + '/' + self.name + '_graph_density.png')
		if save_type == 'all' or (save_type == 'current' and colormap == 3):
			self.graph_window.save_fig(file + '/' + self.name + '_graph_density.png')
		self.color_map_select = 1
		self.change_colormap(self.color_map_select)
		self.apply_masks()
		image = Image.fromarray(self.displayImage)
		if save_type == 'all' or (save_type == 'current' and colormap == 1):
			image.save(file + '/' + self.name + '_image_TauM.tif')
			self.graph_window.save_fig(file + '/' + self.name + '_graph_TauM.png')
		self.color_map_select = 2
		self.change_colormap(self.color_map_select)
		self.apply_masks()
		image = Image.fromarray(self.displayImage)
		if save_type == 'all' or (save_type == 'current' and colormap == 2):
			image.save(file + '/' + self.name + '_image_TauP.tif')
			self.graph_window.save_fig(file + '/' + self.name + '_graph_TauP.png')
		self.color_map_select = 3
		self.apply_masks()
		image = Image.fromarray(self.displayImage)
		if save_type == 'all' or (save_type == 'current' and colormap == 3):
			image.save(file + '/' + self.name + '_image_Jet.tif')
			# self.graph_window.save_fig(file + '/' + self.name + '_graph_density.png')
		self.color_map_select = 4
		self.change_colormap(self.color_map_select)
		self.apply_masks()
		image = Image.fromarray(self.displayImage)

		if save_type == 'all' or (save_type == 'current' and colormap == 4):
			image.save(file + '/' + self.name + '_image_Fraction.tif')
			self.graph_window.save_fig(file + '/' + self.name + '_graph_Fraction.png')
		# When you select the colormaps between intensity (0) and Jet (3), the old code changed the value inside of
		# the function self.change_colormap(). Now, it causes an error if you plug in the same values as what's currenty
		# displayed. Therefore, for some reason, you need to change the value of self.color_map_select before running
		# the function
		if colormap == 3:
			self.color_map_select = 0
			self.change_colormap(0)
		else:
			self.color_map_select = 3
			self.change_colormap(colormap)

		coors = self.x_adjusted.copy()
		coors[mask] = float("nan")
		x_avg = np.average(coors[~mask])
		tifffile.imsave(file + '/' + self.name + '_g.tiff', coors.reshape(self.original_image.shape))
		coors = self.y_adjusted.copy()
		coors[mask] = float("nan")
		y_avg = np.average(coors[~mask])
		tifffile.imsave(file + '/' + self.name + '_s.tiff', coors.reshape(self.original_image.shape))

		arr = self.angle_arr.copy()
		omega = 2 * np.pi * self.freq / 1000
		tau_p = 1 / omega * arr
		tau_p[mask] = float("nan")
		if save_type == 'all' or (save_type == 'current' and colormap == 2):
			tifffile.imsave(file + '/' + self.name + '_TauP.tiff', tau_p)

		arr = self.distance_arr.copy()
		omega = 2 * np.pi * self.freq / 1000
		tau_m = 1 / omega * np.sqrt(1 / np.power(arr, 2) - 1)
		tau_m[mask] = float("nan")
		if save_type == 'all' or (save_type == 'current' and colormap == 1):
			tifffile.imsave(file + '/' + self.name + '_TauM.tiff', tau_m)

		frac = self.fraction_arr.copy()
		frac[mask] = float("nan")
		if save_type == 'all' or (save_type == 'current' and colormap == 4):
			tifffile.imsave(file + '/' + self.name + '_Frac.tiff', frac)

		save_params = [f'number Of 3x3 Median Filters: {self.num_filter}\n',
					   f'Intensity Min: {self.min_thresh:.3f}\n',
					   f'Intensity Max: {self.max_thresh:.3f}\n',
					   f'Phi Min (Deg, ns): ({self.applied_min_ang:.3f}, {1 / omega * np.tan(np.deg2rad(self.applied_min_ang)):.3f}) \n',
					   f'Phi Max (Deg, ns): ({self.applied_max_ang:.3f}, {1 / omega * np.tan(np.deg2rad(self.applied_max_ang)):.3f})\n',
					   f'Modulation Min (M, ns): ({self.applied_min_M/100:.3f}, {1 / omega * np.sqrt(1 / np.power(self.applied_min_M/100, 2) - 1):.3f})\n',
					   f'Modulation Max (M, ns): ({self.applied_max_M/100:.3f}, {1 / omega * np.sqrt(1 / np.power(self.applied_max_M/100, 2) - 1):.3f})\n',
					   f'Fraction Bound Coordinates (g,s): {self.x_fraction:.3f}, {self.y_fraction:.3f}\n',
					   f'Fraction Min: {self.fraction_min:.3f}\n',
					   f'Fraction Max: {self.fraction_max:.3f}\n\n\n',
					   f'Average g Coordinate: {x_avg:.3f}\n',
					   f'Average s Coordinate: {y_avg:.3f}\n',
					   f'Average TauP (ns): {np.nanmean(tau_p):.3f}\n',
					   f'Average TauM (ns): {np.nanmean(tau_m):.3f}\n',
					   f'Average fraction: {np.nanmean(frac):.3f}\n']

		with open(file + '/' + self.name + '_Parameters.txt', 'w') as f:
			f.writelines(save_params)
