"""Code adapted from Maria Belotti's script"""

import numpy as np
import pandas as pd
import csv, scipy
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pytz
import pyart
from wsrlib import *


def xyr2geo(x, y, r, dim=600, rmax=150000, k=1.0):
    '''
    Convert from
        image coordinates in pixels,
        where xy are the center, x axis starts with West, y axis starts with North
    to
        geometric distance in meters from radar, where
        a positive x means East,
        a positive y means North
    '''

    x, y, r = float(x), float(y), float(r)

    x0 = y0 = dim / 2.0  # origin
    x =  (x - x0) * 2 * rmax / dim
    y = -(y - y0) * 2 * rmax / dim
    r = r * k * 2 * rmax / dim  # Note: scaling by k may cause the r to be larger than the scope

    return (x, y, r)


def get_bird_rcs(mass):
    '''
    Return presumed radar cross section of a bird given its mass in grams.

    Parameters
    ----------
    mass: float
        mass of the bird species in grams (refer to Handbook of Body Masses by Dunning, 2008)

    Returns
    -------
    rcs: float
        radar cross section of given speces in cm^2
    '''

    return 10 ** (0.699 * np.log10(mass))


def get_horizontal_beamwidth(number_of_azimuths):
    '''
    Get the horizontal beamwidth of the current radar data in degrees. These angles are usually reported in degrees,
    but we convert them to radians for manipulation.

    Parameters
    ----------
    number_of_azimuths: int
        number of azimuth bins in the current radar data

    Returns
    -------
    theta: float
        the horizontal beamwidth angle (in radians)
    '''

    # Array of possible horizontal resolutions:
    array = np.array([360, 720])

    # Find the index of the value closest to the number of azimuths:
    idx = (np.abs(array - number_of_azimuths)).argmin()

    # Number of angular bins available:
    angular_bins = array[idx]

    # Calculate the angle of each bin, convert to radians:
    theta_rad = np.deg2rad(360 / angular_bins)

    return theta_rad


def get_sampling_volume(theta_rad, phi_rad, rng_gate, rngs, equation="chilson"):
    '''
    Get the sampling volume for each range-along-the-azimuth distance, depending on the year and the
    range gate of the current radar data loaded.

    Parameters
    ----------
    theta_rad: float
        horizontal beamwidth angle in radians
    phi_rad: float
        vertical beamwidth angle in radians
    rng_gate: float
        distance between subsequent cells along the range
    rngs: array
        ranges along the azimuth obtained from the radar scan

    Returns
    -------
    volume_range: array
        returns an array containing the sampling volume in cubic kilometers for each range-along-the-azimuth distance
    '''
    if equation == "chilson":
        # Calculate volume in cubic meters:
        volume_range = (
            (0.35 * np.sqrt(2 * np.pi)) / (2 * np.log(2))
        ) * (
            np.pi * (rngs ** 2) * rng_gate * (theta_rad * phi_rad)
        ) / 4

        # Convert to cubic kilometers to match reflectivity units:
        volume_range = volume_range * 10 ** -9

        return volume_range

    elif equation == "rinehart":
        print("Using Rinehart volume.")
        # Calculate volume in cubic meters:
        volume_range = np.pi * rngs**2 * theta_rad * phi_rad * rng_gate / (8 * np.log(2))

        # Convert to cubic kilometers to match reflectivity units:
        volume_range = volume_range * 10**-9

        return volume_range


def get_unique_sweeps(radar):
    '''
    Sometimes the radar does the same sweep elevation twice to adjust for range folding.
    If the current file has duplicated sweeps, this function will select the first one from
    the list, assuming this will have the lowest nyquist velocity.

    Parameters
    ----------
    radar: Radar
        Py-Art radar object

    Returns
    -------
    sweep_inds: array
        Array with the indexes of the unique sweeps.

    '''
    fixed_angles = radar.fixed_angle["data"]

    sweep_inds = []

    for angle in fixed_angles:
        unique_inds = np.where(np.abs(fixed_angles - angle) <= 0.3)[0]

        if len(unique_inds) > 1:
            unique_inds = unique_inds[0]
        else:
            unique_inds = int(unique_inds)

        if unique_inds not in sweep_inds:
            sweep_inds.append(unique_inds)

    sweep_indexes = np.array(sweep_inds)
    sweep_angles = fixed_angles[sweep_indexes]
    return sweep_indexes, sweep_angles


def calc_n_animals(
    radar,
    sweep_index,
    detection_coordinates,
    rcs,
    xcorr_threshold=np.nan,  # dualpol cross-correlation filtering
    linZ_threshold=np.nan,  # reflectivity filtering
):
    '''
    Calculates the number of animals within a bounding box defined by detection_coordinates, in a scan loaded as a
    pyart object radar. This assumes a conical radar sampling volume.

    Parameters
    ----------
    radar: Radar
        Py-Art radar object
    sweep_index: int
        index of the sweep in the Py-Art format (first is 0)
    detection_coordinates: tuple
        a tuple containing the (x, y) coordinates of the roost and the roost radius in meters
    rcs: float
        radar cross section of target species
    xcorr_threshold: float (from 0 to 1)
        pixels with cross correlation ratio above this value will be set to 0 and considered as rain.
        If NaN, no filtering is applied.
    linZ_threshold: float
        over this value given in linear scale, reflectivity will be set to zero.
        If NaN, no filtering is applied.

    Returns
    -------
    n_roost_pixels: int
        number of radar product pixels of the bounding box
    n_xcorrAboveC_pixels: int or "" if xcorr_threshold is np.nan
        number of pixels where cross correlation ratio was above xcorr_threshold in the bounding box
    n_xcorrBelowC_refAboveD_pixels: int or "" if linZ_threshold is np.nan
        number of pixels where reflectivity is above the linZ_threshold in the bounding box
    n_xcorrBelowC_refBelowD_animals: float
        number of animals calculated by chosen method
    '''

    # Get sampled ranges in meters:
    rngs = radar.range['data']

    # Get range gate in meters:
    rng_gate = radar.range["meters_between_gates"]

    # Get the cartesian coordinates of each gate (sampling bin):
    coords = radar.get_gate_x_y_z(sweep=sweep_index)
    coords = np.array(coords)

    # Retrieve sweep and convert to reflectivity (eta):
    sweep = radar.get_field(sweep=sweep_index, field_name="reflectivity")

    # If the pixel is NaN, we will set it to the least possible value in dBZ scale:
    # TODO: this will cause many nan pixels to be considered high xcorr pixels
    # TODO: implement a NAN mask
    sweep = sweep.filled(-33)

    # Convert dBZ to m^2/km^3:
    sweep, _ = z_to_refl(idb(sweep))

    # Get the shape of the sweep matrix:
    number_of_azimuths = sweep.shape[0]
    number_of_ranges = sweep.shape[1]

    # Separate the results in two 2-D matrices, one for x-coordinates, one for y-coordinates:
    # Note: we will have, for each combination of azimuth and range, the correspoding value
    # of x and of y.
    x = coords[0]
    y = coords[1]

    # Get the unique values, meaning the entire range of possible coordinates along the x and y axis:
    x_unique = np.unique(x)
    y_unique = np.unique(y)

    x_c, y_c, r_c = detection_coordinates

    # Get a rectangle of radius rc around the center of the roost:
    x_inds = np.where(np.abs(x_unique - x_c) < r_c)
    y_inds = np.where(np.abs(y_unique - y_c) < r_c)

    # Find rectangle maximum and minimum values along each axis:
    x_min = min(x_unique[x_inds])
    x_max = max(x_unique[x_inds])
    y_min = min(y_unique[y_inds])
    y_max = max(y_unique[y_inds])

    # Use the extreme values to create a mask. 1 if inside the bounding box, 0 if outside:
    bb_mask = ((x > x_min) & (x < x_max) & (y > y_min) & (y < y_max)).astype(int)

    theta_rad = get_horizontal_beamwidth(number_of_azimuths)
    phi_rad = np.deg2rad(1)

    volume_range = get_sampling_volume(theta_rad, phi_rad, rng_gate, rngs)

    # Apply mask to sweep matrix, 0 if outside bounding box:
    masked = sweep * bb_mask
    # masked should not have negative values, but adding this to set negatives to 0 just in case
    masked = masked * (masked >= 0)

    # Get the total number of pixels in the roost bounding box:
    n_roost_pixels = sum(sum(masked > 0))  # masked cannot be negative

    # If there is dualpol data in scan AND user requested dual pol filtering, apply filter:
    if "cross_correlation_ratio" in radar.fields and not np.isnan(xcorr_threshold):
        # Retrieve cross correlation ratio and create mask:
        cross_correlation = radar.get_field(sweep=sweep_index, field_name="cross_correlation_ratio")
        cross_correlation = cross_correlation.filled(0)
        # 1 to keep a pixel if it has no or low xcorr
        correlation_mask = np.zeros(cross_correlation.shape)
        correlation_mask[cross_correlation < xcorr_threshold] = 1

        # 1 if a pixel has no or low xcorr and is inside the bounding box
        correlation_mask = correlation_mask * bb_mask * (masked >= 0)

        # Pixels within the bounding box that have low cross correlation
        n_xcorrAboveC_pixels = n_roost_pixels - sum(sum(correlation_mask == 1))

        # Apply cross correlation mask to sweep:
        masked = masked * correlation_mask
    else:
        n_xcorrAboveC_pixels = ""

    # If linZ_threshold is not empty, use it to filter:
    if not np.isnan(linZ_threshold):
        n_xcorrBelowC_refAboveD_pixels = sum(sum(masked > linZ_threshold))
        masked[masked > linZ_threshold] = 0
    else:
        n_xcorrBelowC_refAboveD_pixels = ""

    # Create an intermediate array where each cell is a multiplication of reflectivity and volume:
    # This 2-D array will have the same dimensions as the raw radar data:
    roost_matrix = masked * volume_range / rcs
    n_xcorrBelowC_refBelowD_animals = sum(sum(roost_matrix))

    return (
        n_roost_pixels,
        n_xcorrAboveC_pixels,
        n_xcorrBelowC_refAboveD_pixels,
        n_xcorrBelowC_refBelowD_animals
    )

