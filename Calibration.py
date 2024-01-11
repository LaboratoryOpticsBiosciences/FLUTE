import numpy as np
from skimage import io


def get_calibration_parameters(filename, bin_width=0.2208, freq=80, harmonic=1, tau_ref=4):
    """Calculates the calibration parameters for a given image file.

    Args:
        filename (str): Path to the TIFF image file.
        bin_width (float, optional): Width of the time bin in milliseconds. Defaults to 0.2208.
        freq (int, optional): Stimulation frequency in Hz. Defaults to 80.
        harmonic (int, optional): Stimulation harmonic. Defaults to 1.
        tau_ref (int, optional): Refractory period in milliseconds. Defaults to 4.

    Returns:
        Tuple[float, float]: The phi and m offsets for the calibration parameters.
    """

    # Load image data and reshape into (height, width, num_bins) array
    image = np.moveaxis(io.imread(filename), 0, 2)
    height, width, num_bins = image.shape

    # Compute time array and integral image
    t_arr = np.linspace(bin_width / 2, bin_width * (num_bins - 1 / 2), num_bins)
    integral = np.sum(image, axis=2).astype(float)
    integral[integral == 0] = 0.00001

    # Compute g and s phasor coordinates
    cos_term = np.cos(2 * np.pi * freq / 1000 * harmonic * t_arr[:])
    g = np.sum(image[:, ...] * cos_term, axis=2) / integral
    sin_term = np.sin(2 * np.pi * freq / 1000 * harmonic * t_arr[:])
    s = np.sum(image[:, ...] * sin_term, axis=2) / integral

    # Compute mean phasor coordinates of the image
    g_mean = np.mean(g)
    s_mean = np.mean(s)

    # Compute ideal phasor coordinates based on known sample parameters
    omega = 2 * np.pi * freq / 1000
    x_ideal = 1 / (1 + np.power(omega * tau_ref, 2))
    y_ideal = omega * tau_ref / (1 + np.power(omega * tau_ref, 2))
    phi_ideal = np.arctan2(y_ideal, x_ideal)
    m_ideal = np.linalg.norm([x_ideal, y_ideal])

    # Compute actual phasor coordinates of the image
    coor_x = g_mean
    coor_y = s_mean
    phi_given = np.arctan2(coor_y, coor_x)
    m_given = np.linalg.norm([coor_x, coor_y])

    # Compute calibration parameters
    if coor_x < 0:
        theta = phi_ideal - np.pi - phi_given
    else:
        theta = phi_ideal - phi_given
    m = m_ideal / m_given

    return theta, m
