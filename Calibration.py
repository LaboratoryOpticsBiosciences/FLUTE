# Calculates the calibration parameters and returns the phi and m offsets

# imports
import numpy as np
from skimage import io


def get_calibration_parameters(filename, bin_width=0.2208, freq=80, harmonic=1, tau_ref = 4):
	"""Opens the tiff image file and calculates the fft and gets the center coordinates of the g and s. Returns
	the angle and distance that these values need to be translated by to place the calibration measurement
	at the position expected by the user"""
	im = io.imread(filename)
	image = np.moveaxis(im, 0, 2)
	bins = image.shape[2]
	t_arr = np.linspace(bin_width / 2, bin_width * (bins - 1 / 2), bins)

	integral = np.sum(image, axis=2).astype(float)
	integral[integral == 0] = 0.00001
	g = np.sum(image[:, ...] * np.cos(2 * np.pi * freq / 1000 * harmonic * t_arr[:]), axis=2) / integral
	s = np.sum(image[:, ...] * np.sin(2 * np.pi * freq / 1000 * harmonic * t_arr[:]), axis=2) / integral

	g_coor = g.flatten()
	s_coor = s.flatten()

	# Calculates the phi and m that needs to be applied to phasor coordinates to calibrate the software
	# Known sample parameters based on tau and freq
	freq = float(freq)
	tau_ref = float(tau_ref)
	x_ideal = 1 / (1 + np.power(2 * np.pi * freq / 1000 * tau_ref, 2))
	y_ideal = 2 * np.pi * freq / 1000 * tau_ref / (1 + np.power(2 * np.pi * freq / 1000 * tau_ref, 2))

	phi_ideal = np.arctan(y_ideal / x_ideal)
	m_ideal = np.sqrt(x_ideal ** 2 + y_ideal ** 2)
	# Our samples coordinates
	coor_x = np.mean(g_coor)
	coor_y = np.mean(s_coor)
	phi_given = np.arctan(coor_y / coor_x)
	m_given = np.sqrt(coor_x ** 2 + coor_y ** 2)
	# calibration parameters
	if coor_x < 0:
		theta = phi_ideal - np.pi - phi_given
	else:
		theta = phi_ideal - phi_given
	m = m_ideal / m_given
	return theta, m